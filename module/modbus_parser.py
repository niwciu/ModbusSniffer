# --------------------------------------------------------------------------- #
# This file contain parisng code extracted from origin forked version to a class
# keep in project to have option for testing against new builded parser in 
#   mudbus_parser_new.py
# --------------------------------------------------------------------------- #

from datetime import datetime  # for timestamps

class ModbusParser:
    def __init__(self, main_logger, csv_logger, raw_log=False, trashdata = False, on_parsed=None ):
        self.raw_log = raw_log
        self.trashdata = trashdata
        self.csv_logger = csv_logger
        self.log = main_logger
        self.on_parsed = on_parsed

        # Dictionary to remember the last read request (start address, quantity)
        # keyed by (slave_id, function_code)
        self.pendingRequests = {}

        # Inicjalizuj inne właściwości klasy
    # --------------------------------------------------------------------------- #
    # Debuffer and decode the modbus frames (Request, Response, Exception)
    # --------------------------------------------------------------------------- #
    def decodeModbus(self,data):
        modbusdata = data
        bufferIndex = 0
        parsed_frames = []  # nowa lista do gromadzenia wyników

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
                    # Request size
                    expectedLenght = 8
                    if len(modbusdata) >= (frameStartIndex + expectedLenght):
                        bufferIndex = frameStartIndex + 2
                        readAddress = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        readQuantity = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        bufferIndex += 2
                        crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.raw_log:
                                raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                self.log.info(f"Raw Message: {raw_message}")
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                self.log.info(self.trashdataf)

                            request = True
                            responce = False
                            error = False
                            if functionCode == 1:
                                functionCodeMessage = 'Read Coils'
                            else:
                                functionCodeMessage = 'Read Discrete Inputs'
                            self.log.info(
                                "Master\t-> ID: {}, {}: 0x{:02x}, Read address: {}, Read Quantity: {}".format(
                                    unitIdentifier, functionCodeMessage, functionCode, readAddress, readQuantity
                                )
                            )
                            parsed_frames = {
                                "timestamp": datetime.now().isoformat(),
                                "direction": "master",
                                "slave_id": unitIdentifier,
                                "function": functionCode,
                                "data_qty": readQuantity,
                                "function_name": functionCodeMessage,
                                "message_type": "request",
                                "data_address": readAddress,
                                "data":[]
                            }
    
                            modbusdata = modbusdata[bufferIndex:]
                            bufferIndex = 0
                        else:
                            # CRC mismatch; treat as trash data or ignore
                            pass
                    else:
                        needMoreData = True

                    if request == False:
                        # Responce size
                        expectedLenght = 7  # 5 + n
                        if len(modbusdata) >= (frameStartIndex + expectedLenght):
                            bufferIndex = frameStartIndex + 2
                            readByteCount = modbusdata[bufferIndex]
                            bufferIndex += 1
                            expectedLenght = 5 + readByteCount
                            if len(modbusdata) >= (frameStartIndex + expectedLenght):
                                for index in range(readByteCount):
                                    readData.append(modbusdata[bufferIndex])
                                    bufferIndex += 1

                                crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                                metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                                bufferIndex += 2
                                if crc16 == metCRC16:
                                    if self.raw_log:
                                        raw_message = ' '.join(
                                            f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex]
                                        )
                                        self.log.info(f"Raw Message: {raw_message}")
                                    if self.trashdata:
                                        self.trashdata = False
                                        self.trashdataf += "]"
                                        self.log.info(self.trashdataf)
                                    request = False
                                    responce = True
                                    error = False
                                    if functionCode == 1:
                                        functionCodeMessage = 'Read Coils'
                                    else:
                                        functionCodeMessage = 'Read Discrete Inputs'
                                    self.log.info(
                                        "Slave\t-> ID: {}, {}: 0x{:02x}, Read byte count: {}, Read data: [{}]".format(
                                            unitIdentifier,
                                            functionCodeMessage,
                                            functionCode,
                                            readByteCount,
                                            ", ".join(
                                                [
                                                    str(int.from_bytes(readData[i : i + 2], byteorder='big'))
                                                    for i in range(0, len(readData), 2)
                                                ]
                                            ),
                                        )
                                    )
                                    parsed_frames={
                                        "timestamp": datetime.now().isoformat(),
                                        "direction": "slave",
                                        "slave_id": unitIdentifier,
                                        "function": functionCode,
                                        "data_qty": readByteCount,
                                        "data": [
                                            int.from_bytes(readData[i:i+2], byteorder='big')
                                            for i in range(0, len(readData), 2)
                                        ],
                                        "function_name": functionCodeMessage,
                                        "message_type": "response",
                                        "data_address":[]
                                    }

                                    modbusdata = modbusdata[bufferIndex:]
                                    bufferIndex = 0
                                else:
                                    # CRC mismatch; treat as trash data or ignore
                                    pass
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
                        crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.raw_log:
                                # Log the raw message
                                raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                self.log.info(f"Raw Message: {raw_message}")
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                self.log.info(self.trashdataf)
                            request = True

                            # Store the readAddress and readQuantity for this (slave, funcCode).
                            # We'll log to CSV once we get the response.
                            self.pendingRequests[(unitIdentifier, functionCode)] = (
                                readAddress,
                                readQuantity,
                                datetime.now().isoformat()  # store request time if you like
                            )

                            responce = False
                            error = False
                            if functionCode == 3:
                                functionCodeMessage = 'Read Holding Registers'
                            else:
                                functionCodeMessage = 'Read Input Registers'
                            self.log.info("Master\t-> ID: {}, {}: 0x{:02x}, Read address: {}, Read Quantity: {}".format(unitIdentifier, functionCodeMessage, functionCode, readAddress, readQuantity))
                            parsed_frames={
                                "timestamp": datetime.now().isoformat(),
                                "direction": "master",
                                "slave_id": unitIdentifier,
                                "function": functionCode,
                                "data_address": readAddress,
                                "data_qty": readQuantity,
                                "message_type": "request",
                                "function_name": functionCodeMessage,
                                "data":[]
                            }

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
                                crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                                metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                                bufferIndex += 2
                                if crc16 == metCRC16:
                                    if self.raw_log:
                                        # Log the raw message
                                        raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                        self.log.info(f"Raw Message: {raw_message}")
                                    if self.trashdata:
                                        self.trashdata = False
                                        self.trashdataf += "]"
                                        self.log.info(self.trashdataf)
                                    request = False
                                    responce = True
                                    error = False
                                    register_values = []
                                    for i in range(0, len(readData), 2):
                                        val = int.from_bytes(readData[i:i+2], byteorder='big')
                                        register_values.append(val)
                                    if functionCode == 3:
                                        functionCodeMessage = 'Read Holding Registers'
                                    else:
                                        functionCodeMessage = 'Read Input Registers'
                                    self.log.info("Slave\t-> ID: {}, {}: 0x{:02x}, Read byte count: {}, Read data: [{}]".format(
                                        unitIdentifier, functionCodeMessage, functionCode, readByteCount, 
                                        ", ".join([str(int.from_bytes(readData[i:i+2], byteorder='big')) for i in range(0, len(readData), 2)])
                                    ))
                                    parsed_frames={
                                        "timestamp": datetime.now().isoformat(),
                                        "direction": "slave",
                                        "slave_id": unitIdentifier,
                                        "function": functionCode,
                                        "data_qty": readByteCount,
                                        "data": register_values,  # z istniejącego kodu CSV-loga
                                        "message_type": "response",
                                        "data_address":[],
                                        "function_name": functionCodeMessage,
                                    }


                                    # ========== CSV LOGGING FOR DECODED VALUES ========== 
                                    # Grab the request info if we have it
                                    pending = self.pendingRequests.pop((unitIdentifier, functionCode), None)
                                    if pending:
                                        (startReg, quantity, req_time) = pending
                                        # `readData` is a bytearray of length readByteCount
                                        # Each register is 2 bytes
                                        register_values = []
                                        for i in range(0, len(readData), 2):
                                            val = int.from_bytes(readData[i:i+2], byteorder='big')
                                            register_values.append(val)

                                        # We can choose to use the response time rather than the request time:
                                        timestamp_str = datetime.now().isoformat()

                                        # Log the data to CSV
                                        if self.csv_logger:
                                            self.csv_logger.log_data(
                                                timestamp_str,
                                                unitIdentifier,
                                                "READ", 
                                                startReg,
                                                len(register_values),
                                                register_values
                                            )

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
                        crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.raw_log:
                                # Log the raw message
                                raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                self.log.info(f"Raw Message: {raw_message}")
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                self.log.info(self.trashdataf)
                            request = True
                            responce = False
                            error = False
                            self.log.info("Master\t-> ID: {}, Write Single Coil: 0x{:02x}, Write address: {}, Write data: [{}]".format(
                                unitIdentifier, functionCode, writeAddress, 
                                ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                            ))
                            parsed_frames={
                                "timestamp": datetime.now().isoformat(),
                                "direction": "master",
                                "slave_id": unitIdentifier,
                                "function": functionCode,
                                "function_name": "Write Single Coil",
                                "data_address": writeAddress,
                                "data": writeData,
                                "message_type": "request"
                            }
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    self.log.info(f"Raw Message: {raw_message}")
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    self.log.info(self.trashdataf)
                                request = False
                                responce = True
                                error = False
                                self.log.info("Slave\t-> ID: {}, Write Single Coil: 0x{:02x}, Write address: {}".format(unitIdentifier, functionCode, writeAddress))
                                parsed_frames={
                                    "timestamp": datetime.now().isoformat(),
                                    "direction": "slave",
                                    "slave_id": unitIdentifier,
                                    "function": functionCode,
                                    "function_name": "Write Single Coil",
                                    "data_address": writeAddress,
                                    "message_type": "response"
                                }
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
                        crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.raw_log:
                                # Log the raw message
                                raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                self.log.info(f"Raw Message: {raw_message}")
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                self.log.info(self.trashdataf)
                            request = True
                            responce = False
                            error = False
                            self.log.info("Master\t-> ID: {}, Write Single Register: 0x{:02x}, Write address: {}, Write data: [{}]".format(
                                unitIdentifier, functionCode, writeAddress, 
                                ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                            ))
                            parsed_frames={
                                "timestamp": datetime.now().isoformat(),
                                "direction": "master",
                                "slave_id": unitIdentifier,
                                "function": functionCode,
                                "function_name": "Write Single Register",
                                "data_address": writeAddress,
                                "data": writeData,
                                "message_type": "request"
                            }
                            # ---- CSV Logging: single register => quantity=1
                            if self.csv_logger:
                                timestamp_str = datetime.now().isoformat()
                                val = int.from_bytes(writeData, byteorder="big")
                                self.csv_logger.log_data(
                                    timestamp_str,
                                    unitIdentifier,
                                    "WRITE",
                                    writeAddress,
                                    1,         # single register
                                    [val]      # list of length 1
                                )

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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    self.log.info(f"Raw Message: {raw_message}")
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    self.log.info(self.trashdataf)
                                request = False
                                responce = True
                                error = False
                                self.log.info("Slave\t-> ID: {}, Write Single Register: 0x{:02x}, Write address: {}, Write data: [{}]".format(unitIdentifier, functionCode, writeAddress, " ".join(["{:02x}".format(x) for x in writeData])))
                                parsed_frames={
                                    "timestamp": datetime.now().isoformat(),
                                    "direction": "slave",
                                    "slave_id": unitIdentifier,
                                    "function": functionCode,
                                    "function_name": "Write Single Register",
                                    "data_address": writeAddress,
                                    "data": writeData,
                                    "message_type": "respons"
                                }
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    self.log.info(f"Raw Message: {raw_message}")
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    self.log.info(self.trashdataf)
                                request = True
                                responce = False
                                error = False
                                self.log.info("Master\t-> ID: {}, Write Multiple Coils: 0x{:02x}, Write address: {}, Write quantity: {}, Write data: [{}]".format(
                                    unitIdentifier, functionCode, writeAddress, writeQuantity, 
                                    ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                                ))
                                parsed_frames={
                                    "timestamp": datetime.now().isoformat(),
                                    "direction": "master",
                                    "slave_id": unitIdentifier,
                                    "function": functionCode,
                                    "function_name": "Write Multiple Coils",
                                    "data_address": writeAddress,
                                    "data_qty": writeQuantity,
                                    "data": writeData,
                                    "message_type": "request"
                                }
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    self.log.info(f"Raw Message: {raw_message}")
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    self.log.info(self.trashdataf)
                                request = False
                                responce = True
                                error = False
                                self.log.info("Slave\t-> ID: {}, Write Multiple Coils: 0x{:02x}, Write address: {}, Write Quantity: {}".format(unitIdentifier, functionCode, writeAddress, writeQuantity))
                                parsed_frames={
                                    "timestamp": datetime.now().isoformat(),
                                    "direction": "slave",
                                    "slave_id": unitIdentifier,
                                    "function": functionCode,
                                    "function_name": "Write Multiple Coils",
                                    "data_address": writeAddress,
                                    "data_qty": writeQuantity,
                                    "message_type": "response",
                                    "data": "",
                                }
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    self.log.info(f"Raw Message: {raw_message}")
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    self.log.info(self.trashdataf)
                                request = True
                                responce = False
                                error = False
                                self.log.info("Master\t-> ID: {}, Write Multiple registers: 0x{:02x}, Write address: {}, Write quantity: {}, Write data: [{}]".format(
                                    unitIdentifier, functionCode, writeAddress, writeQuantity, 
                                    ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                                ))
                                parsed_frames={
                                    "timestamp": datetime.now().isoformat(),
                                    "direction": "master",
                                    "slave_id": unitIdentifier,
                                    "function": functionCode,
                                    "function_name": "Write Multiple Registers",
                                    "data_address": writeAddress,
                                    "data_qty": writeQuantity,
                                    "data": writeData,
                                    "message_type": "request"
                                }
                                                                # ---- CSV logging:
                                # The user is writing 'writeQuantity' registers,
                                # each register is 2 bytes in writeData.
                                register_values = []
                                for i in range(0, len(writeData), 2):
                                    val = int.from_bytes(writeData[i:i+2], byteorder="big")
                                    register_values.append(val)

                                if self.csv_logger:
                                    timestamp_str = datetime.now().isoformat()
                                    self.csv_logger.log_data(
                                        timestamp_str,
                                        unitIdentifier,
                                        "WRITE",
                                        writeAddress,
                                        writeQuantity,
                                        register_values
                                    )

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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    self.log.info(f"Raw Message: {raw_message}")
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    self.log.info(self.trashdataf)
                                request = False
                                responce = True
                                error = False
                                self.log.info("Slave\t-> ID: {}, Write Multiple registers: 0x{:02x}, Write address: {}, Write quantity: {}".format(unitIdentifier, functionCode, writeAddress, writeQuantity))
                                parsed_frames={
                                    "timestamp": datetime.now().isoformat(),
                                    "direction": "slave",
                                    "slave_id": unitIdentifier,
                                    "function": functionCode,
                                    "function_name": "Write Multiple Registers",
                                    "data_address": writeAddress,
                                    "data_qty": writeQuantity,
                                    "message_type": "response"
                                }
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    self.log.info(f"Raw Message: {raw_message}")
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    self.log.info(self.trashdataf)
                                request = False
                                responce = False
                                error = True
                                self.log.info("Slave\t-> ID: {}, Write Multiple registers: 0x{:02x}, Exception: {}".format(unitIdentifier, functionCode, exceptionCode))
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    self.log.info(f"Raw Message: {raw_message}")
                                if self.trashdata:
                                    self.trashdata = False
                                    self.trashdataf += "]"
                                    self.log.info(self.trashdataf)
                                request = True
                                responce = False
                                error = False
                                self.log.info("Master\t-> ID: {}, Read/Write Multiple registers: 0x{:02x}, Read address: {}, Read Quantity: {}, Write address: {}, Write quantity: {}, Write data: [{}]".format(
                                    unitIdentifier, functionCode, readAddress, readQuantity, writeAddress, writeQuantity, 
                                    ", ".join([str(int.from_bytes(writeData[i:i+2], byteorder='big')) for i in range(0, len(writeData), 2)])
                                ))
                                parsed_frames={
                                    "timestamp": datetime.now().isoformat(),
                                    "direction": "master",
                                    "slave_id": unitIdentifier,
                                    "function": functionCode,
                                    "function_name": "Read/Write Multiple Registers",
                                    "read_address": readAddress,
                                    "read_quantity": readQuantity,
                                    "write_address": writeAddress,
                                    "write_quantity": writeQuantity,
                                    "data": writeData,
                                    "message_type": "request"
                                }
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
                                crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                                metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                                bufferIndex += 2
                                if crc16 == metCRC16:
                                    if self.raw_log:
                                        # Log the raw message
                                        raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                        self.log.info(f"Raw Message: {raw_message}")
                                    if self.trashdata:
                                        self.trashdata = False
                                        self.trashdataf += "]"
                                        self.log.info(self.trashdataf)
                                    request = False
                                    responce = True
                                    error = False
                                    self.log.info("Slave\t-> ID: {}, Read/Write Multiple registers: 0x{:02x}, Read byte count: {}, Read data: [{}]".format(
                                        unitIdentifier, functionCode, readByteCount, 
                                        ", ".join([str(int.from_bytes(readData[i:i+2], byteorder='big')) for i in range(0, len(readData), 2)])
                                    ))   
                                    parsed_frames={
                                        "timestamp": datetime.now().isoformat(),
                                        "direction": "slave",
                                        "slave_id": unitIdentifier,
                                        "function": functionCode,
                                        "function_name": "Read/Write Multiple Registers",
                                        "read_byte_count": readByteCount,
                                        "read_data": readData,
                                        "message_type": "response"
                                    }                             
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
                        crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    self.log.info(f"Raw Message: {raw_message}")
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                self.log.info(self.trashdataf)
                            request = False
                            responce = False
                            error = True
                            self.log.info("Slave\t-> ID: {}, Exception: 0x{:02x}, Code: {}".format(unitIdentifier, functionCode, exceptionCode))
                            parsed_frames={
                                "timestamp": datetime.now().isoformat(),
                                "direction": "slave",
                                "slave_id": unitIdentifier,
                                "function": functionCode,
                                "function_name": "Exception",
                                "exception_code": exceptionCode,
                                "message_type": "response"
                            }
                            modbusdata = modbusdata[bufferIndex:]
                            bufferIndex = 0
                    else:
                        needMoreData = True

            else:
                needMoreData = True
                
            if self.on_parsed:
                if parsed_frames:
                    self.on_parsed(parsed_frames)
            if needMoreData:
                return modbusdata
            elif (request == False) & (responce == False) & (error == False):
                if self.trashdata:
                    self.trashdataf += " {:02x}".format(modbusdata[frameStartIndex])
                else:
                    self.trashdata = True
                    self.trashdataf = "\033[33mWarning \033[0m: Ignoring data: [{:02x}".format(
                        modbusdata[frameStartIndex]
                    )
                bufferIndex = frameStartIndex + 1
                modbusdata = modbusdata[bufferIndex:]
                bufferIndex = 0
    # --------------------------------------------------------------------------- #
    # Calculate the modbus CRC
    # --------------------------------------------------------------------------- #
    def calcCRC16(self, data, size):
        crcHi = 0XFF
        crcLo = 0xFF
        
        crcHiTable  = [ 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
                        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
                        0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
                        0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
                        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1,
                        0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41,
                        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1,
                        0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
                        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
                        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40,
                        0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1,
                        0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
                        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
                        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40,
                        0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
                        0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
                        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
                        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
                        0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
                        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
                        0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
                        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40,
                        0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1,
                        0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
                        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
                        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40]

        crcLoTable = [  0x00, 0xC0, 0xC1, 0x01, 0xC3, 0x03, 0x02, 0xC2, 0xC6, 0x06,
                        0x07, 0xC7, 0x05, 0xC5, 0xC4, 0x04, 0xCC, 0x0C, 0x0D, 0xCD,
                        0x0F, 0xCF, 0xCE, 0x0E, 0x0A, 0xCA, 0xCB, 0x0B, 0xC9, 0x09,
                        0x08, 0xC8, 0xD8, 0x18, 0x19, 0xD9, 0x1B, 0xDB, 0xDA, 0x1A,
                        0x1E, 0xDE, 0xDF, 0x1F, 0xDD, 0x1D, 0x1C, 0xDC, 0x14, 0xD4,
                        0xD5, 0x15, 0xD7, 0x17, 0x16, 0xD6, 0xD2, 0x12, 0x13, 0xD3,
                        0x11, 0xD1, 0xD0, 0x10, 0xF0, 0x30, 0x31, 0xF1, 0x33, 0xF3,
                        0xF2, 0x32, 0x36, 0xF6, 0xF7, 0x37, 0xF5, 0x35, 0x34, 0xF4,
                        0x3C, 0xFC, 0xFD, 0x3D, 0xFF, 0x3F, 0x3E, 0xFE, 0xFA, 0x3A,
                        0x3B, 0xFB, 0x39, 0xF9, 0xF8, 0x38, 0x28, 0xE8, 0xE9, 0x29,
                        0xEB, 0x2B, 0x2A, 0xEA, 0xEE, 0x2E, 0x2F, 0xEF, 0x2D, 0xED,
                        0xEC, 0x2C, 0xE4, 0x24, 0x25, 0xE5, 0x27, 0xE7, 0xE6, 0x26,
                        0x22, 0xE2, 0xE3, 0x23, 0xE1, 0x21, 0x20, 0xE0, 0xA0, 0x60,
                        0x61, 0xA1, 0x63, 0xA3, 0xA2, 0x62, 0x66, 0xA6, 0xA7, 0x67,
                        0xA5, 0x65, 0x64, 0xA4, 0x6C, 0xAC, 0xAD, 0x6D, 0xAF, 0x6F,
                        0x6E, 0xAE, 0xAA, 0x6A, 0x6B, 0xAB, 0x69, 0xA9, 0xA8, 0x68,
                        0x78, 0xB8, 0xB9, 0x79, 0xBB, 0x7B, 0x7A, 0xBA, 0xBE, 0x7E,
                        0x7F, 0xBF, 0x7D, 0xBD, 0xBC, 0x7C, 0xB4, 0x74, 0x75, 0xB5,
                        0x77, 0xB7, 0xB6, 0x76, 0x72, 0xB2, 0xB3, 0x73, 0xB1, 0x71,
                        0x70, 0xB0, 0x50, 0x90, 0x91, 0x51, 0x93, 0x53, 0x52, 0x92,
                        0x96, 0x56, 0x57, 0x97, 0x55, 0x95, 0x94, 0x54, 0x9C, 0x5C,
                        0x5D, 0x9D, 0x5F, 0x9F, 0x9E, 0x5E, 0x5A, 0x9A, 0x9B, 0x5B,
                        0x99, 0x59, 0x58, 0x98, 0x88, 0x48, 0x49, 0x89, 0x4B, 0x8B,
                        0x8A, 0x4A, 0x4E, 0x8E, 0x8F, 0x4F, 0x8D, 0x4D, 0x4C, 0x8C,
                        0x44, 0x84, 0x85, 0x45, 0x87, 0x47, 0x46, 0x86, 0x82, 0x42,
                        0x43, 0x83, 0x41, 0x81, 0x80, 0x40]

        index = 0
        while index < size:
            crc = crcHi ^ data[index]
            crcHi = crcLo ^ crcHiTable[crc]
            crcLo = crcLoTable[crc]
            index += 1

        metCRC16 = (crcHi * 0x0100) + crcLo
        return metCRC16
