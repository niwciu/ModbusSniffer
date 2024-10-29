#!/usr/bin/env python

"""
Python modbus sniffer implementation
---------------------------------------------------------------------------

The following is an modbus RTU sniffer program,
made without the use of modbus specific library.
"""
# --------------------------------------------------------------------------- #
# import the various needed libraries
# --------------------------------------------------------------------------- #
import signal
import sys
import getopt
import logging
import serial
from datetime import datetime
import crcmod

# Initialize the Modbus CRC-16 function using crcmod
modbus_crc16 = crcmod.predefined.mkCrcFun("modbus")

# --------------------------------------------------------------------------- #
# configure the logging system
# --------------------------------------------------------------------------- #

class MyFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            self._style._fmt = "%(asctime)-15s %(message)s"
        elif record.levelno == logging.DEBUG:
            self._style._fmt = f"%(asctime)-15s \033[36m%(levelname)-8s\033[0m: %(message)s"
        else:
            color = {
                logging.WARNING: 33,
                logging.ERROR: 31,
                logging.FATAL: 31,
            }.get(record.levelno, 0)
            self._style._fmt = f"%(asctime)-15s \033[{color}m%(levelname)-8s %(threadName)-15s-%(module)-15s:%(lineno)-8s\033[0m: %(message)s"
        return super().format(record)
    
def configure_logging(log_to_file):
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    # Console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(MyFormatter())
    log.addHandler(console_handler)

    if log_to_file:
        # File handler with custom formatter, using current datetime for filename
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_handler = logging.FileHandler(f'log_{current_time}.log')
        file_handler.setFormatter(MyFormatter())
        log.addHandler(file_handler)

    return log

# --------------------------------------------------------------------------- #
# declare the sniffer
# --------------------------------------------------------------------------- #
class SerialSnooper:

    def __init__(self, port, baud=9600, parity=serial.PARITY_EVEN, timeout=0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.parity = parity

        log.info("Opening serial interface: \n" + "\tport: {} \n".format(port) + "\tbaudrate: {}\n".format(baud) + "\tbytesize: 8\n" + "\tparity: {}\n".format(parity) + "\tstopbits: 1\n" + "\ttimeout: {}\n".format(timeout))
        self.connection = serial.Serial(port=port, baudrate=baud, bytesize=serial.EIGHTBITS, parity=parity, stopbits=serial.STOPBITS_ONE, timeout=timeout)
        log.debug(self.connection)

        # Global variables
        self.data = bytearray(0)
        self.trashdata = False
        self.trashdataf = bytearray(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        self.connection.open()

    def close(self):
        self.connection.close()
    
    def read_raw(self, n=1):
        return self.connection.read(n)

    # --------------------------------------------------------------------------- #
    # Bufferise the data and call the decoder if the interframe timeout occur.
    # --------------------------------------------------------------------------- #
    def process_data(self, data):
        if len(data) <= 0:
            if len(self.data) > 2:
                self.data = self.decodeModbus(self.data)
            return
        for dat in data:
            self.data.append(dat)

    # --------------------------------------------------------------------------- #
    # Debuffer and decode the modbus frames (Request, Responce, Exception)
    # --------------------------------------------------------------------------- #
    def decodeModbus(self, data):
        modbusdata = data
        bufferIndex = 0

        while True:
            unitIdentifier = 0
            functionCode = 0
            readAddress = 0
            readQuantity = 0
            readByteCount = 0
            readData = bytearray(0)
            writeAddress = 0
            writeQuantity = 0
            writeByteCount = 0
            writeData = bytearray(0)
            exceptionCode = 0
            crc16 = 0
            request = False
            responce = False
            error = False
            needMoreData = False

            frameStartIndex = bufferIndex

            if len(modbusdata) > (frameStartIndex + 2):
                # Unit Identifier (Slave Address)
                unitIdentifier = modbusdata[bufferIndex]
                bufferIndex += 1
                # Function Code
                functionCode = modbusdata[bufferIndex]
                bufferIndex += 1
                # FC01 (0x01) Read Coils  FC02 (0x02) Read Discrete Inputs
                if functionCode in (1, 2):
                    # Request size: UnitIdentifier (1) + FunctionCode (1) + ReadAddress (2) + ReadQuantity (2) + CRC (2)
                    expectedLenght = 8 # 8
                    if len(modbusdata) >= (frameStartIndex + expectedLenght):
                        bufferIndex = frameStartIndex + 2
                        # Read Address (2)
                        readAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Read Quantity (2)
                        readQuantity = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # CRC16 (2)
                        crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                log.info(self.trashdataf)

                            request = True
                            responce = False
                            error = False
                            if functionCode == 1:
                                functionCodeMessage = 'Read Coils'
                            else:
                                functionCodeMessage = 'Read Discrete Inputs'
                            log.info("Master\t\t-> ID: {}, {}: 0x{:02x}, Read address: {}, Read Quantity: {}".format(unitIdentifier, functionCodeMessage, functionCode, readAddress, readQuantity))
                            modbusdata = modbusdata[bufferIndex:]
                            bufferIndex = 0
                    else:
                        needMoreData = True
                    
                    if (request == False):
                        # Responce size: UnitIdentifier (1) + FunctionCode (1) + ReadByteCount (1) + ReadData (n) + CRC (2)
                        expectedLenght = 7 # 5 + n (n >= 2)
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            bufferIndex = frameStartIndex + 2
                            # Read Byte Count (1)
                            readByteCount = modbusdata[bufferIndex]
                            bufferIndex += 1
                            expectedLenght = (5 + readByteCount)
                            if len(modbusdata) >= (frameStartIndex + expectedLenght):
                                # Read Data (n)
                                index = 1
                                while index <= readByteCount:
                                    readData.append(modbusdata[bufferIndex])
                                    bufferIndex += 1
                                    index += 1
                                # CRC16 (2)
                                crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                                metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                                bufferIndex += 2
                                if crc16 == metCRC16:
                                    if self.trashdata:
                                        self.trashdata = False
                                        self.trashdataf += "]"
                                        log.info(self.trashdataf)
                                    request = False
                                    responce = True
                                    error = False
                                    if functionCode == 1:
                                        functionCodeMessage = 'Read Coils'
                                    else:
                                        functionCodeMessage = 'Read Discrete Inputs'
                                        log.info("Slave\t-> ID: {}, {}: 0x{:02x}, Read byte count: {}, Read data: [{}]".format(
                                            unitIdentifier, functionCodeMessage, functionCode, readByteCount, 
                                            ", ".join([str(int.from_bytes(readData[i:i+2], byteorder='big')) for i in range(0, len(readData), 2)])
                                        ))
                                    modbusdata = modbusdata[bufferIndex:]
                                    bufferIndex = 0
                            else:
                                needMoreData = True
                        else:
                            needMoreData = True

                # FC03 (0x03) Read Holding Registers  FC04 (0x04) Read Input Registers
                elif functionCode in (3, 4):
                    # Request size: UnitIdentifier (1) + FunctionCode (1) + ReadAddress (2) + ReadQuantity (2) + CRC (2)
                    expectedLenght = 8 # 8
                    if len(modbusdata) >= (frameStartIndex + expectedLenght):
                        bufferIndex = frameStartIndex + 2
                        # Read Address (2)
                        readAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Read Quantity (2)
                        readQuantity = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # CRC16 (2)
                        crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                log.info(self.trashdataf)
                            request = True
                            responce = False
                            error = False
                            if functionCode == 3:
                                functionCodeMessage = 'Read Holding Registers'
                            else:
                                functionCodeMessage = 'Read Input Registers'
                            log.info("Master\t-> ID: {}, {}: 0x{:02x}, Read address: {}, Read Quantity: {}".format(unitIdentifier, functionCodeMessage, functionCode, readAddress, readQuantity))
                            modbusdata = modbusdata[bufferIndex:]
                            bufferIndex = 0
                    else:
                        needMoreData = True

                    if (request == False):
                        # Responce size: UnitIdentifier (1) + FunctionCode (1) + ReadByteCount (1) + ReadData (n) + CRC (2)
                        expectedLenght = 7 # 5 + n (n >= 2)
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            bufferIndex = frameStartIndex + 2
                            # Read Byte Count (1)
                            readByteCount = modbusdata[bufferIndex]
                            bufferIndex += 1
                            expectedLenght = (5 + readByteCount)
                            if len(modbusdata) >= (frameStartIndex + expectedLenght):
                                # Read Data (n)
                                index = 1
                                while index <= readByteCount:
                                    readData.append(modbusdata[bufferIndex])
                                    bufferIndex += 1
                                    index += 1
                                # CRC16 (2)
                                crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                                metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                                bufferIndex += 2
                                if crc16 == metCRC16:
                                    if self.trashdata:
                                        self.trashdata = False
                                        self.trashdataf += "]"
                                        log.info(self.trashdataf)
                                    request = False
                                    responce = True
                                    error = False
                                    if functionCode == 3:
                                        functionCodeMessage = 'Read Holding Registers'
                                    else:
                                        functionCodeMessage = 'Read Input Registers'
                                    log.info("Slave\t-> ID: {}, {}: 0x{:02x}, Read byte count: {}, Read data: [{}]".format(
                                        unitIdentifier, functionCodeMessage, functionCode, readByteCount, 
                                        ", ".join([str(int.from_bytes(readData[i:i+2], byteorder='big')) for i in range(0, len(readData), 2)])
                                    ))
                                    modbusdata = modbusdata[bufferIndex:]
                                    bufferIndex = 0
                            else:
                                needMoreData = True
                        else:
                            needMoreData = True

                # FC05 (0x05) Write Single Coil
                elif (functionCode == 5):
            
                    # Request size: UnitIdentifier (1) + FunctionCode (1) + WriteAddress (2) + WriteData (2) + CRC (2)
                    expectedLenght = 8
                    if len(modbusdata) >= (frameStartIndex + expectedLenght):
                        bufferIndex = frameStartIndex + 2
                        # Write Address (2)
                        writeAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Write Data (2)
                        writeData.append(modbusdata[bufferIndex])
                        bufferIndex += 1
                        writeData.append(modbusdata[bufferIndex])
                        bufferIndex += 1
                        # CRC16 (2)
                        crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                log.info(self.trashdataf)
                            request = True
                            responce = False
                            error = False
                            log.info("Master\t-> ID: {}, Write Single Coil: 0x{:02x}, Write address: {}, Write data: [{}]".format(
                                unitIdentifier, functionCode, writeAddress, 
                                ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                            ))
                            modbusdata = modbusdata[bufferIndex:]
                            bufferIndex = 0
                    else:
                        needMoreData = True
                    
                    if (request == False):
                        # Responce size: UnitIdentifier (1) + FunctionCode (1) + WriteAddress (2) + CRC (2)
                        expectedLenght = 6
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            bufferIndex = frameStartIndex + 2
                            # Write Address (2)
                            writeAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            bufferIndex += 2
                            # CRC16 (2)
                            crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    log.info(self.trashdataf)
                                request = False
                                responce = True
                                error = False
                                log.info("Slave\t-> ID: {}, Write Single Coil: 0x{:02x}, Write address: {}".format(unitIdentifier, functionCode, writeAddress))
                                modbusdata = modbusdata[bufferIndex:]
                                bufferIndex = 0
                        else:
                            needMoreData = True

                # FC06 (0x06) Write Single Register
                elif (functionCode == 6):
        
                    # Request size: UnitIdentifier (1) + FunctionCode (1) + WriteAddress (2) + WriteData (2) + CRC (2)
                    expectedLenght = 8
                    if len(modbusdata) >= (frameStartIndex + expectedLenght):
                        bufferIndex = frameStartIndex + 2
                        # Write Address (2)
                        writeAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Write Data (2)
                        writeData.append(modbusdata[bufferIndex])
                        bufferIndex += 1
                        writeData.append(modbusdata[bufferIndex])
                        bufferIndex += 1
                        # CRC16 (2)
                        crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                log.info(self.trashdataf)
                            request = True
                            responce = False
                            error = False
                            log.info("Master\t-> ID: {}, Write Single Register: 0x{:02x}, Write address: {}, Write data: [{}]".format(
                                unitIdentifier, functionCode, writeAddress, 
                                ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                            ))
                            modbusdata = modbusdata[bufferIndex:]
                            bufferIndex = 0
                    else:
                        needMoreData = True
                    
                    if (request == False):
                    # Responce size: UnitIdentifier (1) + FunctionCode (1) + WriteAddress (2) + WriteData (2) + CRC (2)
                        expectedLenght = 8
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            bufferIndex = frameStartIndex + 2
                            # Write Address (2)
                            writeAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            bufferIndex += 2
                            # Write Data (2)
                            writeData.append(modbusdata[bufferIndex])
                            bufferIndex += 1
                            writeData.append(modbusdata[bufferIndex])
                            bufferIndex += 1
                            # CRC16 (2)
                            crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    log.info(self.trashdataf)
                                request = False
                                responce = True
                                error = False
                                log.info("Slave\t-> ID: {}, Write Single Register: 0x{:02x}, Write address: {}, Write data: [{}]".format(unitIdentifier, functionCode, writeAddress, " ".join(["{:02x}".format(x) for x in writeData])))
                                modbusdata = modbusdata[bufferIndex:]
                                bufferIndex = 0
                        else:
                            needMoreData = True

                # FC07 (0x07) Read Exception Status (Serial Line only)
                # elif (functionCode == 7):
                
                # FC08 (0x08) Diagnostics (Serial Line only)
                # elif (functionCode == 8):
                
                # FC11 (0x0B) Get Comm Event Counter (Serial Line only)
                # elif (functionCode == 11):
                
                # FC12 (0x0C) Get Comm Event Log (Serial Line only)
                # elif (functionCode == 12):
                    
                # FC15 (0x0F) Write Multiple Coils
                elif (functionCode == 15):
                    
                    # Request size: UnitIdentifier (1) + FunctionCode (1) + WriteAddress (2) + WriteQuantity (2) + WriteByteCount (1) + WriteData (n) + CRC (2)
                    expectedLenght = 10 # n >= 1
                    if len(modbusdata) >= (frameStartIndex + expectedLenght):
                        bufferIndex = frameStartIndex + 2
                        # Write Address (2)
                        writeAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Write Quantity (2)
                        writeQuantity = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Write Byte Count (1)
                        writeByteCount = modbusdata[bufferIndex]
                        bufferIndex += 1
                        expectedLenght = (9 + writeByteCount)
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            # Write Data (n)
                            index = 1
                            while index <= writeByteCount:
                                writeData.append(modbusdata[bufferIndex])
                                bufferIndex += 1
                                index += 1
                            # CRC16 (2)
                            crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    log.info(self.trashdataf)
                                request = True
                                responce = False
                                error = False
                                log.info("Master\t-> ID: {}, Write Multiple Coils: 0x{:02x}, Write address: {}, Write quantity: {}, Write data: [{}]".format(
                                    unitIdentifier, functionCode, writeAddress, writeQuantity, 
                                    ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                                ))
                                modbusdata = modbusdata[bufferIndex:]
                                bufferIndex = 0
                        else:
                            needMoreData = True
                    else:
                        needMoreData = True
                    
                    if (request == False):
                    # Responce size: UnitIdentifier (1) + FunctionCode (1) + WriteAddress (2) + WriteQuantity (2) + CRC (2)
                        expectedLenght = 8
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            bufferIndex = frameStartIndex + 2
                            # Write Address (2)
                            writeAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            bufferIndex += 2
                            # Write Quantity (2)
                            writeQuantity = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            bufferIndex += 2
                            # CRC16 (2)
                            crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    log.info(self.trashdataf)
                                request = False
                                responce = True
                                error = False
                                log.info("Slave\t-> ID: {}, Write Multiple Coils: 0x{:02x}, Write address: {}, Write Quantity: {}".format(unitIdentifier, functionCode, writeAddress, writeQuantity))
                                modbusdata = modbusdata[bufferIndex:]
                                bufferIndex = 0
                        else:
                            needMoreData = True

                # FC16 (0x10) Write Multiple registers
                elif (functionCode == 16):
                    
                    # Request size: UnitIdentifier (1) + FunctionCode (1) + WriteAddress (2) + WriteQuantity (2) + WriteByteCount (1) + WriteData (n) + CRC (2)
                    expectedLenght = 11 # n >= 2
                    if len(modbusdata) >= (frameStartIndex + expectedLenght):
                        bufferIndex = frameStartIndex + 2
                        # Write Address (2)
                        writeAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Write Quantity (2)
                        writeQuantity = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Write Byte Count (1)
                        writeByteCount = modbusdata[bufferIndex]
                        bufferIndex += 1
                        expectedLenght = (9 + writeByteCount)
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            # Write Data (n)
                            index = 1
                            while index <= writeByteCount:
                                writeData.append(modbusdata[bufferIndex])
                                bufferIndex += 1
                                index += 1
                            # CRC16 (2)
                            crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    log.info(self.trashdataf)
                                request = True
                                responce = False
                                error = False
                                log.info("Master\t-> ID: {}, Write Multiple registers: 0x{:02x}, Write address: {}, Write quantity: {}, Write data: [{}]".format(
                                    unitIdentifier, functionCode, writeAddress, writeQuantity, 
                                    ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                                ))
                                modbusdata = modbusdata[bufferIndex:]
                                bufferIndex = 0
                        else:
                            needMoreData = True
                    else:
                        needMoreData = True
                    
                    if (request == False):
                    # Responce size: UnitIdentifier (1) + FunctionCode (1) + WriteAddress (2) + WriteQuantity (2) + CRC (2)
                        expectedLenght = 8
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            bufferIndex = frameStartIndex + 2
                            # Write Address (2)
                            writeAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            bufferIndex += 2
                            # Write Quantity (2)
                            writeQuantity = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            bufferIndex += 2
                            # CRC16 (2)
                            crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    log.info(self.trashdataf)
                                request = False
                                responce = True
                                error = False
                                log.info("Slave\t-> ID: {}, Write Multiple registers: 0x{:02x}, Write address: {}, Write quantity: {}".format(unitIdentifier, functionCode, writeAddress, writeQuantity))
                                modbusdata = modbusdata[bufferIndex:]
                                bufferIndex = 0
                        else:
                            needMoreData = True

                    if (request == False) & (responce == False):
                        # Error size: UnitIdentifier (1) + FunctionCode (1) + ExceptionCode (1) + CRC (2)
                        expectedLenght = 5 # 5
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            bufferIndex = frameStartIndex + 2
                            # Exception Code (1)
                            exceptionCode = modbusdata[bufferIndex]
                            bufferIndex += 1
                            
                            # CRC16 (2)
                            crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    log.info(self.trashdataf)
                                request = False
                                responce = False
                                error = True
                                log.info("Slave\t-> ID: {}, Write Multiple registers: 0x{:02x}, Exception: {}".format(unitIdentifier, functionCode, exceptionCode))
                                modbusdata = modbusdata[bufferIndex:]
                                bufferIndex = 0
                        else:
                            needMoreData = True

                # FC17 (0x11) Report Server ID (Serial Line only)
                # elif (functionCode == 17):
                    
                # FC20 (0x14) Read File Record
                # elif (functionCode == 20):
                    
                # FC21 (0x15) Write File Record
                # elif (functionCode == 21):
                    
                # FC22 (0x16) Mask Write Register
                # elif (functionCode == 22):
                    
                # FC23 (0x17) Read/Write Multiple registers
                elif (functionCode == 23):
                
                    # Request size: UnitIdentifier (1) + FunctionCode (1) + ReadAddress (2) + ReadQuantity (2) + WriteAddress (2) + WriteQuantity (2) + WriteByteCount (1) + WriteData (n) + CRC (2)
                    expectedLenght = 15 # 13 + n (n >= 2)
                    if len(modbusdata) >= (frameStartIndex + expectedLenght):
                        bufferIndex = frameStartIndex + 2
                        # Read Address (2)
                        readAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Read Quantity (2)
                        readQuantity = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Write Address (2)
                        writeAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Write Quantity (2)
                        writeQuantity = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        # Write Byte Count (1)
                        writeByteCount = modbusdata[bufferIndex]
                        bufferIndex += 1
                        expectedLenght = (13 + writeByteCount)
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            # Write Data (n)
                            index = 1
                            while index <= writeByteCount:
                                writeData.append(modbusdata[bufferIndex])
                                bufferIndex += 1
                                index += 1
                            # CRC16 (2)
                            crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    log.info(self.trashdataf)
                                request = True
                                responce = False
                                error = False
                                log.info("Master\t-> ID: {}, Read/Write Multiple registers: 0x{:02x}, Read address: {}, Read Quantity: {}, Write address: {}, Write quantity: {}, Write data: [{}]".format(
                                    unitIdentifier, functionCode, readAddress, readQuantity, writeAddress, writeQuantity, 
                                    ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                                ))
                                modbusdata = modbusdata[bufferIndex:]
                                bufferIndex = 0
                        else:
                            needMoreData = True
                    else:
                        needMoreData = True
                    
                    if (request == False):
                        # Responce size: UnitIdentifier (1) + FunctionCode (1) + ReadByteCount (1) + ReadData (n) + CRC (2)
                        expectedLenght = 7 # 5 + n (n >= 2)
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            bufferIndex = frameStartIndex + 2
                            # Read Byte Count (1)
                            readByteCount = modbusdata[bufferIndex]
                            bufferIndex += 1
                            expectedLenght = (5 + readByteCount)
                            if len(modbusdata) >= (frameStartIndex + expectedLenght):
                                # Read Data (n)
                                index = 1
                                while index <= readByteCount:
                                    readData.append(modbusdata[bufferIndex])
                                    bufferIndex += 1
                                    index += 1
                                # CRC16 (2)
                                crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                                metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                                bufferIndex += 2
                                if crc16 == metCRC16:
                                    if self.trashdata:
                                        self.trashdata = False
                                        self.trashdataf += "]"
                                        log.info(self.trashdataf)
                                    request = False
                                    responce = True
                                    error = False
                                    log.info("Slave\t-> ID: {}, Read/Write Multiple registers: 0x{:02x}, Read byte count: {}, Read data: [{}]".format(
                                        unitIdentifier, functionCode, readByteCount, 
                                        ", ".join([str(int.from_bytes(readData[i:i+2], byteorder='big')) for i in range(0, len(readData), 2)])
                                    ))                                  
                                    modbusdata = modbusdata[bufferIndex:]
                                    bufferIndex = 0
                            else:
                                needMoreData = True
                        else:
                            needMoreData = True
   
                # FC24 (0x18) Read FIFO Queue
                # elif (functionCode == 24):
                    
                # FC43 ( 0x2B) Encapsulated Interface Transport
                # elif (functionCode == 43):
                
                # FC80+ ( 0x80 + FC) Exeption
                elif (functionCode >= 0x80):
                
                    # Error size: UnitIdentifier (1) + FunctionCode (1) + ExceptionCode (1) + CRC (2)
                    expectedLenght = 5 # 5
                    if len(modbusdata) >= (frameStartIndex + expectedLenght):
                        bufferIndex = frameStartIndex + 2
                        # Exception Code (1)
                        exceptionCode = modbusdata[bufferIndex]
                        bufferIndex += 1
                        
                        # CRC16 (2)
                        crc16 = self.read_uint16_le(modbusdata, bufferIndex)
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                log.info(self.trashdataf)
                            request = False
                            responce = False
                            error = True
                            log.info("Slave\t-> ID: {}, Exception: 0x{:02x}, Code: {}".format(unitIdentifier, functionCode, exceptionCode))
                            modbusdata = modbusdata[bufferIndex:]
                            bufferIndex = 0
                    else:
                        needMoreData = True

            else:
                needMoreData = True

            if needMoreData:
                return modbusdata
            elif (request == False) & (responce == False) & (error == False):
                if self.trashdata:
                    self.trashdataf += " {:02x}".format(modbusdata[frameStartIndex])
                else:
                    self.trashdata = True
                    self.trashdataf = "\033[33mWarning \033[0m: Ignoring data: [{:02x}".format(modbusdata[frameStartIndex])
                bufferIndex = frameStartIndex + 1
                modbusdata = modbusdata[bufferIndex:]
                bufferIndex = 0

    # --------------------------------------------------------------------------- #
    # Calculate the modbus CRC
    # --------------------------------------------------------------------------- #
    def read_uint16_le(self, data, index):
        return data[index] + (data[index + 1] << 8)    # Calculate the CRC on the provided data slice up to the specified size
    
    def calcCRC16(self, data, size):
        crc = modbus_crc16(data[:size])
        # Swap bytes to match Modbus little-endian CRC
        crc_le = ((crc & 0xFF) << 8) | (crc >> 8)
        return crc_le


# --------------------------------------------------------------------------- #
# Print the usage help
# --------------------------------------------------------------------------- #
def printHelp(baud, parity, log_to_file, timeout):
    if timeout == None:
        timeout = calcTimeout(baud)
    print("\nUsage:")
    print("  python modbus_sniffer.py [arguments]")
    print("")
    print("Arguments:")
    print("  -p, --port        select the serial port (Required)")
    print("  -b, --baudrate    set the communication baud rate, default = {} (Option)".format(baud))
    print("  -r, --parity      select parity, default = {} (Option)".format(parity))
    print("  -t, --timeout     override the calculated inter frame timeout, default = {}s (Option)".format(timeout))
    print("  -l, --log-to-file console log is written to file, default = {} (Option)".format(log_to_file))
    print("  -h, --help        print the documentation")
    print("")
    # print("  python3 {} -p <serial port> [-b baudrate, default={}] [-t timeout, default={}]".format(sys.argv[0], baud, timeout))

# --------------------------------------------------------------------------- #
# Calculate the timeout with the baudrate
# --------------------------------------------------------------------------- #
def calcTimeout(baud):
    # Modbus states that a baud rate higher than 19200 must use a 1.75 ms for a frame delay.
    # For baud rates below 19200 the timeing is more critical and has to be calculated.
    # In modbus a character is made of a data byte that appends a start bit, stop bit,
    # and parity bit which mean in RTU mode, there are 11 bits per character.
    # Though the "Character-Time" calculation is 11 bits/char / [baud rate] bits/sec.
    # Modbus standard states a frame delay must be 3.5T or 3.5 times longer than 
    # a normal character.
    # E.g. for 9600 baud:
    # "Character-Time": 11 / 9600 = 0.0011458s 
    # "Frame delay": 11 * 3.5 = 38.5
    #                38.5 / 9600 = 0.0040104s
    if (baud < 19200):
        timeout = 33 / baud # changed the ratio from 3.5 to 3
    else:
        timeout = 0.001750
    return timeout

# --------------------------------------------------------------------------- #
# configure a clean exit (even with the use of kill, 
# may be useful if saving the data to a file)
# --------------------------------------------------------------------------- #
def signal_handler(sig, frame):
    print('\nGoodbye\n')
    sys.exit(0)

# --------------------------------------------------------------------------- #
# main routine
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    print(" ")
    # init the signal handler for a clean exit
    signal.signal(signal.SIGINT, signal_handler)

    port = None
    baud = 9600
    timeout = None
    parity = serial.PARITY_EVEN
    log_to_file = False

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hp:b:r:t:l",["help", "port=", "baudrate=",  "parity=", "timeout=", "log-to-file"])
    except getopt.GetoptError as e:
        printHelp(baud, parity, log_to_file, timeout)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            printHelp(baud, parity, log_to_file, timeout)
            sys.exit()
        elif opt in ("-p", "--port"):
            port = arg
        elif opt in ("-b", "--baudrate"):
            baud = int(arg)
        elif opt in ("-t", "--timeout"):
            timeout = float(arg)
        elif opt in ("-r", "--parity"):
            if "none" in arg.lower():
                parity = serial.PARITY_NONE
            elif "even" in arg.lower():
                parity = serial.PARITY_EVEN
            elif "odd" in arg.lower():
                parity = serial.PARITY_ODD
        elif opt in ("-l", "--log-to-file"):
            log_to_file = True
    
    log = configure_logging(log_to_file)

    if port == None:
        print("Serial Port not defined please use:")
        printHelp(baud, parity, log_to_file, timeout)
        sys.exit(2)
    
    if timeout == None:
        timeout = calcTimeout(baud)
    
    with SerialSnooper(port, baud, parity, timeout) as sniffer:
        while True:
            data = sniffer.read_raw()
            sniffer.process_data(data)