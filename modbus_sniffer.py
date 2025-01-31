"""
Python modbus sniffer implementation
---------------------------------------------------------------------------

The following is a modbus RTU sniffer program,
made without the use of any modbus-specific library.
"""

import csv
import os
import argparse
import signal
import sys
import logging
import serial
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# --------------------------------------------------------------------------- #
# CSV Logger class
# --------------------------------------------------------------------------- #
class CSVLogger:
    def __init__(self, enable_csv=False, daily_file=False, output_dir=".", base_filename="modbus_data"):
        """
        :param enable_csv: Boolean - if False, this logger does nothing.
        :param daily_file: Boolean - if True, rotate CSV daily (one file per day).
        :param output_dir: Directory where CSV files should be created.
        :param base_filename: The base name for CSV files; date_time will be appended.
        """
        self.enable_csv = enable_csv
        self.daily_file = daily_file
        self.output_dir = output_dir
        self.base_filename = base_filename

        # Keep an internal map of (slave_id, register_address) -> column index
        self.register_map = {}

        # Our running list of columns:
        # 0: Timestamp
        # 1: Slave ID
        # 2: Operation  (READ/WRITE)
        self.columns = ["Timestamp", "Slave ID", "Operation"]

        # Internal references for file handle, CSV writer, etc.
        self.csv_file = None
        self.csv_writer = None

        # Track the current date so we know when to rotate
        self.current_date_str = None

        if self.enable_csv:
            self._open_csv_file()

    def _get_date_str(self):
        """Return YYYYMMDD for daily rotation checks."""
        return datetime.now().strftime("%Y%m%d")

    def _get_datetime_str(self):
        """Return YYYYMMDD_HHMMSS for filenames."""
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def _open_csv_file(self):
        """Open (or reopen) the CSV file. Closes any previously open file."""
        if self.csv_file:
            self.csv_file.close()

        # We always create a filename with date and time
        date_time_str = self._get_datetime_str()
        filename = f"{self.base_filename}_{date_time_str}.csv"

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        fullpath = os.path.join(self.output_dir, filename)

        self.csv_file = open(fullpath, mode="w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)

        # Always write the initial header
        self.csv_writer.writerow(self.columns)
        self.csv_file.flush()

        # If we are using daily rotation, store the current date
        if self.daily_file:
            self.current_date_str = self._get_date_str()

    def _check_daily_rotation(self):
        """If daily_file is True, check if the date changed. If so, open a new file."""
        if not self.daily_file:
            return
        current = self._get_date_str()
        if current != self.current_date_str:
            # Date changed => rotate
            self._open_csv_file()

    def _expand_header_for_registers(self, slave_id, start_register, quantity):
        """
        For each register in [start_register, start_register + quantity - 1],
        ensure we have a column. If new columns are added, rewrite the ENTIRE file
        so the updated header is the FIRST line.
        """
        changed = False
        for offset in range(quantity):
            reg_addr = start_register + offset
            key = (slave_id, reg_addr)
            if key not in self.register_map:
                # Insert a new column
                new_col_name = f"Reg_{slave_id}_{reg_addr}"
                self.columns.append(new_col_name)
                self.register_map[key] = len(self.columns) - 1
                changed = True

        if changed:
            self._rewrite_file_with_new_header()

    def _rewrite_file_with_new_header(self):
        """
        1) Close the file
        2) Read all old data in memory
        3) Create a new file with the same name
        4) Write updated header
        5) Remap old rows into the new columns
        6) Append them
        7) Reopen in append mode for further usage
        """
        if not self.csv_file:
            return

        # Step 1: close the file
        self.csv_file.close()

        # We can get the file path from .name
        old_path = self.csv_file.name

        # Step 2: read all old data in memory
        with open(old_path, mode="r", encoding="utf-8") as f:
            reader = list(csv.reader(f))

        # The first row is the old header
        old_header = reader[0] if reader else []
        old_rows = reader[1:] if len(reader) > 1 else []

        # Step 3: create a new file with the same path, truncated
        with open(old_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Step 4: write updated header
            writer.writerow(self.columns)

            # Step 5 & 6: remap old rows
            # old_header -> self.columns
            # Build a map: old_col_name => old_col_index
            old_col_map = {col_name: idx for idx, col_name in enumerate(old_header)}

            # For each old row, build a new row with the new columns
            for old_row in old_rows:
                new_row = [""] * len(self.columns)
                for col_index, col_name in enumerate(old_header):
                    if col_index < len(old_row):
                        cell_value = old_row[col_index]
                    else:
                        cell_value = ""

                    if col_name in old_col_map:
                        if col_name in self.columns:
                            new_index = self.columns.index(col_name)
                            new_row[new_index] = cell_value

                writer.writerow(new_row)

        # Step 7: reopen the file in append mode
        self.csv_file = open(old_path, mode="a", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)

    def log_data(self, timestamp, slave_id, operation, start_register, quantity, register_values):
        """
        Logs a single row with the given data to the CSV file.

        :param timestamp:        String timestamp
        :param slave_id:         The Modbus slave address
        :param operation:        "READ" or "WRITE"
        :param start_register:   The starting register/coil address
        :param quantity:         How many registers/coils
        :param register_values:  A list of integer values
        """
        if not self.enable_csv:
            return

        self._check_daily_rotation()
        self._expand_header_for_registers(slave_id, start_register, quantity)

        row = [""] * len(self.columns)
        # Fill the fixed columns
        row[0] = timestamp
        row[1] = slave_id
        row[2] = operation

        # Fill register data
        for i, val in enumerate(register_values):
            reg_addr = start_register + i
            col_idx = self.register_map.get((slave_id, reg_addr), None)
            if col_idx is not None:
                row[col_idx] = val

        self.csv_writer.writerow(row)
        self.csv_file.flush()

    def close(self):
        """Close the CSV file if open."""
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None

# --------------------------------------------------------------------------- #
# Custom logging formatter
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

# --------------------------------------------------------------------------- #
# Configure logging
# --------------------------------------------------------------------------- #
def configure_logging(log_to_file, daily_file=False):
    """
    Configure logging to console, plus optionally to a file.
    If daily_file=True, create a new log file at midnight.
    """
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    # Console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(MyFormatter())
    log.addHandler(console_handler)

    if log_to_file:
        # Always create a filename with current date & time
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f'log_{current_time}.log'

        if daily_file:
            # Use a TimedRotatingFileHandler to rotate logs at midnight
            handler = TimedRotatingFileHandler(
                filename,
                when='midnight',
                interval=1,
                backupCount=7,
                encoding='utf-8'
            )
            handler.setFormatter(MyFormatter())
            log.addHandler(handler)
        else:
            file_handler = logging.FileHandler(filename, encoding='utf-8')
            file_handler.setFormatter(MyFormatter())
            log.addHandler(file_handler)

    return log

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Sniffer class
# --------------------------------------------------------------------------- #
class SerialSnooper:
    def __init__(
        self,
        port,
        baud=9600,
        parity=serial.PARITY_EVEN,
        timeout=0,
        raw_log=False,
        raw_only=False,
        csv_log=False,         # <-- NEW
        daily_file=False       # <-- NEW: re-use the same daily-file logic
    ):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.parity = parity
        self.raw_log = raw_log
        self.raw_only = raw_only

        # Our new CSV logger (if requested)
        self.csv_logger = CSVLogger(
            enable_csv=csv_log,
            daily_file=daily_file,
            output_dir=".",  # or "logs" if you prefer
            base_filename="log"
        ) if csv_log else None

        # Dictionary to remember the last read request (start address, quantity)
        # keyed by (slave_id, function_code)
        self.pendingRequests = {}

        log.info(
            "Opening serial interface: \n"
            + f"\tport: {port}\n"
            + f"\tbaudrate: {baud}\n"
            + "\tbytesize: 8\n"
            + f"\tparity: {parity}\n"
            + "\tstopbits: 1\n"
            + f"\ttimeout: {timeout}\n"
        )
        self.connection = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=parity,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
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
        if self.csv_logger:
            self.csv_logger.close()

    def read_raw(self, n=1):
        return self.connection.read(n)

    # --------------------------------------------------------------------------- #
    # Buffer the data and call the decoder if the interframe timeout occurs.
    # --------------------------------------------------------------------------- #
    def process_data(self, data):
        """
        In normal mode: accumulate the data into self.data,
        and decode on inter-frame timeouts.

        In raw-only mode: just logs data as hex and discards it.
        """
        if self.raw_only and data:
            # If the user wants to log raw, produce a hex representation
            raw_message = ' '.join(f"{byte:02x}" for byte in data)
            log.info(f"Raw RS485 data: {raw_message}")
            return  # skip decode entirely

        if len(data) <= 0:
            # Check if we have something that might form a valid modbus frame
            if len(self.data) > 2:
                self.data = self.decodeModbus(self.data)
            return

        # Otherwise, accumulate and decode as normal
        for dat in data:
            self.data.append(dat)

    # --------------------------------------------------------------------------- #
    # Debuffer and decode the modbus frames (Request, Response, Exception)
    # --------------------------------------------------------------------------- #
    def decodeModbus(self, data):
        modbusdata = data
        bufferIndex = 0
        from datetime import datetime  # for timestamps

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
                                log.info(f"Raw Message: {raw_message}")
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
                            log.info(
                                "Master\t\t-> ID: {}, {}: 0x{:02x}, Read address: {}, Read Quantity: {}".format(
                                    unitIdentifier, functionCodeMessage, functionCode, readAddress, readQuantity
                                )
                            )
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
                                        log.info(f"Raw Message: {raw_message}")
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
                                    log.info(
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
                                log.info(f"Raw Message: {raw_message}")
                            if self.trashdata:
                                self.trashdata = False
                                self.trashdataf += "]"
                                log.info(self.trashdataf)
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
                                crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                                metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                                bufferIndex += 2
                                if crc16 == metCRC16:
                                    if self.raw_log:
                                        # Log the raw message
                                        raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                        log.info(f"Raw Message: {raw_message}")
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
                                log.info(f"Raw Message: {raw_message}")
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    log.info(f"Raw Message: {raw_message}")
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
                        crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.raw_log:
                                # Log the raw message
                                raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                log.info(f"Raw Message: {raw_message}")
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
                                    log.info(f"Raw Message: {raw_message}")
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    log.info(f"Raw Message: {raw_message}")
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    log.info(f"Raw Message: {raw_message}")
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    log.info(f"Raw Message: {raw_message}")
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
                                    log.info(f"Raw Message: {raw_message}")
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    log.info(f"Raw Message: {raw_message}")
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
                            crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                            metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                            bufferIndex += 2
                            if crc16 == metCRC16:
                                if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    log.info(f"Raw Message: {raw_message}")
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
                                crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                                metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                                bufferIndex += 2
                                if crc16 == metCRC16:
                                    if self.raw_log:
                                        # Log the raw message
                                        raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                        log.info(f"Raw Message: {raw_message}")
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
                        crc16 = (modbusdata[bufferIndex] * 0x0100) + modbusdata[bufferIndex + 1]
                        metCRC16 = self.calcCRC16(modbusdata, bufferIndex)
                        bufferIndex += 2
                        if crc16 == metCRC16:
                            if self.raw_log:
                                    # Log the raw message
                                    raw_message = ' '.join(f"{byte:02x}" for byte in modbusdata[frameStartIndex:bufferIndex])
                                    log.info(f"Raw Message: {raw_message}")
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

# --------------------------------------------------------------------------- #
# Calculate the default timeout with the baudrate
# --------------------------------------------------------------------------- #
def calcTimeout(baud):
    if baud < 19200:
        # default formula
        timeout = 33 / baud
    else:
        timeout = 0.001750
    return timeout

# --------------------------------------------------------------------------- #
# Clean exit on Ctrl+C
# --------------------------------------------------------------------------- #
def signal_handler(sig, frame):
    print('\nGoodbye\n')
    sys.exit(0)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Initialize Ctrl+C handler
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(
        description="Modbus RTU sniffer that logs decoded frames and optionally raw data."
    )
    parser.add_argument(
        "-p", "--port",
        required=True,
        help="Select the serial port (e.g. COM3, /dev/ttyUSB0)."
    )
    parser.add_argument(
        "-b", "--baudrate",
        type=int,
        default=9600,
        help="Set the communication baud rate (default: 9600)."
    )
    parser.add_argument(
        "-r", "--parity",
        default="even",
        choices=["none", "even", "odd"],
        help="Select parity: none, even, or odd (default: even)."
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=None,
        help="Inter-frame timeout in seconds. If not set, an automatic calculation is used."
    )
    parser.add_argument(
        "-l", "--log-to-file",
        action="store_true",
        default=False,
        help="Write console log to a file as well (default: False)."
    )
    parser.add_argument(
        "-R", "--raw",
        action="store_true",
        default=False,
        help="Also log raw messages in hex (implies --log-to-file)."
    )
    parser.add_argument(
        "-X", "--raw-only",
        action="store_true",
        default=False,
        help="Log only raw traffic in hex, skip decode (implies --log-to-file)."
    )
    parser.add_argument(
        "-D", "--daily-file",
        action="store_true",
        default=False,
        help="Rotate logs daily at midnight (default: False)."
    )
    parser.add_argument(
        "-C", "--csv",
        action="store_true",
        default=False,
        help="Log decoded register data to a CSV file (implies daily rotation)."
    )

    args = parser.parse_args()

    # Convert parity string to pySerial constant
    if args.parity == "none":
        parity = serial.PARITY_NONE
    elif args.parity == "even":
        parity = serial.PARITY_EVEN
    else:
        parity = serial.PARITY_ODD

    # Map command-line flags to local variables
    port = args.port
    baud = args.baudrate
    log_to_file = args.log_to_file
    raw_log = args.raw
    raw_only = args.raw_only
    daily_file = args.daily_file
    csv_log = args.csv

    # If user chooses raw or raw-only, imply log-to-file
    if raw_log or raw_only:
        log_to_file = True

    # If user chooses CSV, also force daily_file = True (so new CSV each day)
    if csv_log:
        daily_file = True

    # Compute default timeout if not given
    if args.timeout is None:
        timeout = calcTimeout(baud)
    else:
        timeout = args.timeout

    # Configure logging
    log = configure_logging(log_to_file, daily_file)

    # Start the sniffer
    with SerialSnooper(
        port=port,
        baud=baud,
        parity=parity,
        timeout=timeout,
        raw_log=raw_log,
        raw_only=raw_only,
        csv_log=csv_log,
        daily_file=daily_file
    ) as sniffer:
        while True:
            data = sniffer.read_raw()
            sniffer.process_data(data)