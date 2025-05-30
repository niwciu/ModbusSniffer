from datetime import datetime


class ModbusParser:
    def __init__(
        self, main_logger, csv_logger, raw_log=False, trashdata=False, on_parsed=None
    ):
        self.raw_log = raw_log
        self.trashdata = trashdata
        self.trashdataf = ""
        self.csv_logger = csv_logger
        self.log = main_logger
        self.on_parsed = on_parsed
        self.pendingRequests = {}

    def decodeModbus(self, data):
        buffer = data
        self.bufferIndex = 0

        while self.bufferIndex < len(buffer):
            frameStartIndex = self.bufferIndex
            if len(buffer) - self.bufferIndex < 2:
                break

            unitIdentifier = buffer[self.bufferIndex]
            self.bufferIndex += 1
            functionCode = buffer[self.bufferIndex]
            self.bufferIndex += 1

            handler = self._get_handler(functionCode)
            if handler:
                result = handler(buffer, frameStartIndex, unitIdentifier, functionCode)
                if result:
                    if self.on_parsed:
                        self.on_parsed(result)
                    buffer = buffer[self.bufferIndex :]
                    self.bufferIndex = 0
                    continue

            self._handle_trash(buffer, frameStartIndex)
            buffer = buffer[frameStartIndex + 1 :]
            self.bufferIndex = 0

        return buffer

    def _get_handler(self, fc):
        def wrapper(request_handler, response_handler):
            def dynamic_handler(buffer, start, sid, fc):
                key = (sid, fc)
                if key not in self.pendingRequests:
                    self.pendingRequests[key] = ("request", datetime.now().isoformat())
                    return request_handler(buffer, start, sid, fc)
                else:
                    self.pendingRequests.pop(key, None)
                    return response_handler(buffer, start, sid, fc)

            return dynamic_handler

        return {
            1: wrapper(self._handle_read_bits, self._handle_read_bits_response),
            2: wrapper(self._handle_read_bits, self._handle_read_bits_response),
            3: wrapper(
                self._handle_read_registers, self._handle_read_registers_response
            ),
            4: wrapper(
                self._handle_read_registers, self._handle_read_registers_response
            ),
            5: wrapper(self._handle_write_single, self._handle_write_single_response),
            6: wrapper(self._handle_write_single, self._handle_write_single_response),
            15: wrapper(
                self._handle_write_multiple, self._handle_write_multiple_response
            ),
            16: wrapper(
                self._handle_write_multiple, self._handle_write_multiple_response
            ),
            23: wrapper(self._handle_read_write, self._handle_read_write_response),
        }.get(fc, self._handle_exception if fc >= 0x80 else None)

    def _is_response_frame(self, buffer, fc, start_index):
        try:
            if fc in [1, 2, 3, 4, 23]:
                byte_count = buffer[start_index + 2]
                expected = start_index + 3 + byte_count + 2
                return len(buffer) >= expected
            elif fc in [5, 6, 15, 16]:
                return len(buffer) >= start_index + 8
            return False
        except IndexError:
            return False

    def _handle_trash(self, buffer, index):
        byte = buffer[index]
        if self.trashdata:
            self.trashdataf += f" {byte:02x}"
        else:
            self.trashdata = True
            self.trashdataf = f"\033[33mWarning \033[0m: Ignoring data: [{
                byte:02x}"
        self.bufferIndex = index + 1

    def _log_raw(self, buffer, start, end):
        if self.raw_log:
            raw_message = " ".join(f"{b:02x}" for b in buffer[start:end])
            self.log.info(f"Raw Message: {raw_message}")

    def _validate_crc(self, buffer, end):
        if end + 1 >= len(buffer):
            return False
        crc = (buffer[end] << 8) + buffer[end + 1]
        return crc == self.calcCRC16(buffer, end)

    def _log_data(self, msg):
        self.log.info(msg)

    def _log_csv(self, timestamp, sid, op, addr, qty, values):
        if self.csv_logger:
            self.csv_logger.log_data(timestamp, sid, op, addr, qty, values)

    def _parse_data_words(self, data):
        return [
            int.from_bytes(data[i : i + 2], byteorder="big")
            for i in range(0, len(data), 2)
        ]

    def _common_frame(self, **kwargs):
        default_frame = {
            # Current timestamp when the frame was created
            "timestamp": datetime.now().isoformat(),
            "slave_id": "",  # Modbus slave ID (unit identifier)
            "function": "",  # Function code of the Modbus operation
            "function_name": "",  # Human-readable name of the function
            # Starting address for the operation (read/write)
            "data_address": "",
            # Quantity of items (coils/registers) to be read or written
            "data_qty": "",
            "byte_cnt": "",  # Number of data bytes in response/request
            "data": [],  # Actual data values (as list of bytes or words)
            "direction": "",  # 'master' or 'slave' - who sent the message
            "message_type": "",  # 'request' or 'response'
            # Optional fields for extended operations like FC23 (Read/Write
            # Multiple Registers)
            # Starting address for the read portion (FC 23)
            "read_address": "",
            "read_quantity": "",  # Quantity of registers to read (FC 23)
            # Starting address for the write portion (FC 23)
            "write_address": "",
            "write_quantity": "",  # Quantity of registers to write (FC 23)
            # Optional field for exception responses
            "exception_code": "",  # Exception code if an error response is returned
        }
        default_frame.update(kwargs)
        return default_frame

    # ---------- Handler Implementations ----------
    def _handle_read_bits(self, buffer, start, sid, fc):
        if len(buffer) < start + 8:
            return None
        read_address = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        read_qty = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        crc_valid = self._validate_crc(buffer, self.bufferIndex)
        self.bufferIndex += 2
        if not crc_valid:
            return None
        self._log_raw(buffer, start, self.bufferIndex)
        self._log_data(
            f"Master\t-> ID: {sid}, FC: 0x{
                fc:02x}, Read address: {read_address}, Read Quantity: {read_qty}"
        )
        self._log_csv(
            datetime.now().isoformat(), sid, "READ", read_address, read_qty, []
        )
        fname = "Read Coils" if fc == 1 else "Read Discrete Inputs"
        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            data_address=read_address,
            data_qty=read_qty,
            # Additional parser data for table view gnerator
            direction="master",
            message_type="request",
            function_name=fname,
        )

    def _handle_read_registers(self, buffer, start, sid, fc):
        if len(buffer) < start + 8:
            return None
        read_address = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        read_qty = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        crc_valid = self._validate_crc(buffer, self.bufferIndex)
        self.bufferIndex += 2
        if not crc_valid:
            return None
        self._log_raw(buffer, start, self.bufferIndex)
        self.pendingRequests[(sid, fc)] = (
            read_address,
            read_qty,
            datetime.now().isoformat(),
        )
        fname = "Read Holding Registers" if fc == 3 else "Read Input Registers"
        self._log_data(
            f"Master\t-> ID: {sid}, FC: 0x{
                fc:02x}, Read address: {read_address}, Read Quantity: {read_qty}"
        )
        self._log_csv(
            datetime.now().isoformat(), sid, "READ", read_address, read_qty, []
        )
        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            data_address=read_address,
            data_qty=read_qty,
            # Additional parser data for table view gnerator
            direction="master",
            message_type="request",
            function_name=fname,
        )

    def _handle_write_single(self, buffer, start, sid, fc):
        if len(buffer) < start + 8:
            return None
        addr = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        data = buffer[self.bufferIndex : self.bufferIndex + 2]
        self.bufferIndex += 2
        crc_valid = self._validate_crc(buffer, self.bufferIndex)
        self.bufferIndex += 2
        if not crc_valid:
            return None
        self._log_raw(buffer, start, self.bufferIndex)
        self._log_data(
            f"Master\t-> ID: {sid}, FC: 0x{
                fc:02x}, Write addr: {addr}, Data: {
                int.from_bytes(
                    data, 'big')}"
        )
        fname = "Write Single Coil" if fc == 5 else "Write Single Register"
        frame = self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            data_address=addr,
            data=list(data),
            # Additional parser data for table view gnerator
            direction="master",
            message_type="request",
            function_name=fname,
        )
        if fc == [5, 6]:
            self._log_csv(
                frame["timestamp"], sid, "WRITE", addr, 1, [int.from_bytes(data, "big")]
            )
        return frame

    def _handle_write_multiple(self, buffer, start, sid, fc):
        if len(buffer) < start + 9:
            return None
        addr = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        qty = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        byte_count = buffer[self.bufferIndex]
        self.bufferIndex += 1
        data = buffer[self.bufferIndex : self.bufferIndex + byte_count]
        self.bufferIndex += byte_count
        crc_valid = self._validate_crc(buffer, self.bufferIndex)
        self.bufferIndex += 2
        if not crc_valid:
            return None
        self._log_raw(buffer, start, self.bufferIndex)
        fname = "Write Multiple Coils" if fc == 15 else "Write Multiple Registers"
        values = self._parse_data_words(data) if fc == 16 else list(data)
        self._log_data(
            f"Master\t-> ID: {sid}, FC: 0x{fc:02x}, Write addr: {addr}, Quantity: {qty}"
        )
        if fc == [15, 16]:
            self._log_csv(datetime.now().isoformat(), sid, "WRITE", addr, qty, values)
        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            data_address=addr,
            data_qty=qty,
            byte_cnt=byte_count,
            data=values,
            # Additional parser data for table view gnerator
            direction="master",
            message_type="request",
            function_name=fname,
        )

    def _handle_read_write(self, buffer, start, sid, fc):
        if len(buffer) < start + 13:
            return None
        read_address = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        read_qty = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        write_address = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        write_qty = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        byte_count = buffer[self.bufferIndex]
        self.bufferIndex += 1
        data = buffer[self.bufferIndex : self.bufferIndex + byte_count]
        self.bufferIndex += byte_count

        if not self._validate_crc(buffer, self.bufferIndex):
            return None
        self.bufferIndex += 2
        self._log_raw(buffer, start, self.bufferIndex)
        values = self._parse_data_words(data)
        self._log_data(
            f"Master\t-> ID: {sid}, FC: 0x{fc:02x}, ReadAddr: {read_address}, ReadQty: {read_qty}, "
            f"WriteAddr: {write_address}, WriteQty: {write_qty}"
        )
        self._log_csv(
            datetime.now().isoformat(), sid, "READ", read_address, read_qty, []
        )
        self._log_csv(
            datetime.now().isoformat(), sid, "WRITE", write_address, write_qty, values
        )
        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            read_address=read_address,
            read_quantity=read_qty,
            write_address=write_address,
            write_quantity=write_qty,
            byte_count=2 * write_qty,
            data=values,
            # Additional parser data for table view gnerator
            direction="master",
            message_type="request",
            function_name="Read/Write Multiple Registers",
        )

    def _handle_exception(self, buffer, start, sid, fc):
        if len(buffer) < start + 5:
            return None
        exception_code = buffer[self.bufferIndex]
        self.bufferIndex += 1
        if not self._validate_crc(buffer, self.bufferIndex):
            return None
        self.bufferIndex += 2
        self._log_raw(buffer, start, self.bufferIndex)
        self._log_data(
            f"Slave\t-> ID: {sid}, Exception FC: 0x{fc:02x}, Code: {exception_code}"
        )
        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,  # this is function code with error mask
            exception_code=exception_code,
            # Additional parser data for table view gnerator
            direction="slave",
            message_type="response",
            function_name="Exception",
        )

    def _handle_read_bits_response(self, buffer, start, sid, fc):
        if len(buffer) < start + 5:
            return None
        byte_count = buffer[self.bufferIndex]
        self.bufferIndex += 1
        if len(buffer) < self.bufferIndex + byte_count + 2:
            return None
        data = buffer[self.bufferIndex : self.bufferIndex + byte_count]
        self.bufferIndex += byte_count
        if not self._validate_crc(buffer, self.bufferIndex):
            return None
        self.bufferIndex += 2
        self._log_raw(buffer, start, self.bufferIndex)
        values = list(data)
        fname = "Read Coils" if fc == 1 else "Read Discrete Inputs"
        self._log_data(
            f"Slave\t-> ID: {sid}, FC: 0x{fc:02x}, Read byte count: {byte_count}, Data: {values}"
        )
        self._log_csv(datetime.now().isoformat(), sid, "READ", "", len(values), values)
        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            byte_cnt=byte_count,
            data=values,
            # Additional parser data for table view gnerator
            direction="slave",
            message_type="response",
            function_name=fname,
        )

    def _handle_read_registers_response(self, buffer, start, sid, fc):
        if len(buffer) < start + 5:
            return None
        byte_count = buffer[self.bufferIndex]
        self.bufferIndex += 1
        if len(buffer) < self.bufferIndex + byte_count + 2:
            return None
        data = buffer[self.bufferIndex : self.bufferIndex + byte_count]
        self.bufferIndex += byte_count
        if not self._validate_crc(buffer, self.bufferIndex):
            return None
        self.bufferIndex += 2
        self._log_raw(buffer, start, self.bufferIndex)
        values = self._parse_data_words(data)
        fname = "Read Holding Registers" if fc == 3 else "Read Input Registers"
        self._log_data(
            f"Slave\t-> ID: {sid}, FC: 0x{fc:02x}, Byte count: {byte_count}, Data: {values}"
        )
        request_info = self.pendingRequests.pop((sid, fc), None)
        if request_info:
            addr, qty, _ = request_info
            self._log_csv(
                datetime.now().isoformat(), sid, "READ", addr, len(values), values
            )
        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            byte_cnt=byte_count,
            data=values,
            # Additional parser data for table view gnerator
            direction="slave",
            message_type="response",
            function_name=fname,
            # data_qty=byte_count//2,
        )

    def _handle_write_single_response(self, buffer, start, sid, fc):
        if len(buffer) < start + 8:
            return None
        addr = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        data = buffer[self.bufferIndex : self.bufferIndex + 2]
        self.bufferIndex += 2
        if not self._validate_crc(buffer, self.bufferIndex):
            return None
        self.bufferIndex += 2
        self._log_raw(buffer, start, self.bufferIndex)
        fname = "Write Single Coil" if fc == 5 else "Write Single Register"
        self._log_data(
            f"Slave\t-> ID: {sid}, FC: 0x{
                fc:02x}, Echo addr: {addr}, Data: {
                int.from_bytes(
                    data, 'big')}"
        )
        self._log_csv(
            datetime.now().isoformat(),
            sid,
            "WRITE",
            addr,
            1,
            [int.from_bytes(data, "big")],
        )

        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            data_address=addr,
            data=list(data),
            # Additional parser data for table view gnerator
            direction="slave",
            message_type="response",
            function_name=fname,
        )

    def _handle_write_multiple_response(self, buffer, start, sid, fc):
        if len(buffer) < start + 8:
            return None
        addr = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        qty = (buffer[self.bufferIndex] << 8) + buffer[self.bufferIndex + 1]
        self.bufferIndex += 2
        if not self._validate_crc(buffer, self.bufferIndex):
            return None
        self.bufferIndex += 2
        self._log_raw(buffer, start, self.bufferIndex)
        fname = "Write Multiple Coils" if fc == 15 else "Write Multiple Registers"
        self._log_data(
            f"Slave\t-> ID: {sid}, FC: 0x{fc:02x}, Echo addr: {addr}, Qty: {qty}"
        )
        self._log_csv(datetime.now().isoformat(), sid, "WRITE", addr, qty, [])

        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            data_address=addr,
            data_qty=qty,
            # Additional parser data for table view gnerator
            direction="slave",
            message_type="response",
            function_name=fname,
            # byte_cnt = qty*2,
        )

    def _handle_read_write_response(self, buffer, start, sid, fc):
        if len(buffer) < start + 5:
            return None
        byte_count = buffer[self.bufferIndex]
        self.bufferIndex += 1
        data = buffer[self.bufferIndex : self.bufferIndex + byte_count]
        self.bufferIndex += byte_count
        if not self._validate_crc(buffer, self.bufferIndex):
            return None
        self.bufferIndex += 2
        self._log_raw(buffer, start, self.bufferIndex)
        values = self._parse_data_words(data)
        self._log_data(
            f"Slave\t-> ID: {sid}, FC: 0x{fc:02x}, Read byte count: {byte_count}, Data: {values}"
        )
        self._log_csv(datetime.now().isoformat(), sid, "READ", "", len(values), values)
        return self._common_frame(
            # MODBUS Application Protocol Specification V1.1b value set
            slave_id=sid,
            function=fc,
            byte_cnt=byte_count,
            data=values,
            # Additional parser data for table view gnerator
            direction="slave",
            message_type="response",
            function_name="Read/Write Multiple Registers",
        )

    # --------------------------------------------------------------------------- #
    # Calculate the modbus CRC
    # --------------------------------------------------------------------------- #
    def calcCRC16(self, data, size):
        crcHi = 0xFF
        crcLo = 0xFF

        crcHiTable = [
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x01,
            0xC0,
            0x80,
            0x41,
            0x00,
            0xC1,
            0x81,
            0x40,
        ]

        crcLoTable = [
            0x00,
            0xC0,
            0xC1,
            0x01,
            0xC3,
            0x03,
            0x02,
            0xC2,
            0xC6,
            0x06,
            0x07,
            0xC7,
            0x05,
            0xC5,
            0xC4,
            0x04,
            0xCC,
            0x0C,
            0x0D,
            0xCD,
            0x0F,
            0xCF,
            0xCE,
            0x0E,
            0x0A,
            0xCA,
            0xCB,
            0x0B,
            0xC9,
            0x09,
            0x08,
            0xC8,
            0xD8,
            0x18,
            0x19,
            0xD9,
            0x1B,
            0xDB,
            0xDA,
            0x1A,
            0x1E,
            0xDE,
            0xDF,
            0x1F,
            0xDD,
            0x1D,
            0x1C,
            0xDC,
            0x14,
            0xD4,
            0xD5,
            0x15,
            0xD7,
            0x17,
            0x16,
            0xD6,
            0xD2,
            0x12,
            0x13,
            0xD3,
            0x11,
            0xD1,
            0xD0,
            0x10,
            0xF0,
            0x30,
            0x31,
            0xF1,
            0x33,
            0xF3,
            0xF2,
            0x32,
            0x36,
            0xF6,
            0xF7,
            0x37,
            0xF5,
            0x35,
            0x34,
            0xF4,
            0x3C,
            0xFC,
            0xFD,
            0x3D,
            0xFF,
            0x3F,
            0x3E,
            0xFE,
            0xFA,
            0x3A,
            0x3B,
            0xFB,
            0x39,
            0xF9,
            0xF8,
            0x38,
            0x28,
            0xE8,
            0xE9,
            0x29,
            0xEB,
            0x2B,
            0x2A,
            0xEA,
            0xEE,
            0x2E,
            0x2F,
            0xEF,
            0x2D,
            0xED,
            0xEC,
            0x2C,
            0xE4,
            0x24,
            0x25,
            0xE5,
            0x27,
            0xE7,
            0xE6,
            0x26,
            0x22,
            0xE2,
            0xE3,
            0x23,
            0xE1,
            0x21,
            0x20,
            0xE0,
            0xA0,
            0x60,
            0x61,
            0xA1,
            0x63,
            0xA3,
            0xA2,
            0x62,
            0x66,
            0xA6,
            0xA7,
            0x67,
            0xA5,
            0x65,
            0x64,
            0xA4,
            0x6C,
            0xAC,
            0xAD,
            0x6D,
            0xAF,
            0x6F,
            0x6E,
            0xAE,
            0xAA,
            0x6A,
            0x6B,
            0xAB,
            0x69,
            0xA9,
            0xA8,
            0x68,
            0x78,
            0xB8,
            0xB9,
            0x79,
            0xBB,
            0x7B,
            0x7A,
            0xBA,
            0xBE,
            0x7E,
            0x7F,
            0xBF,
            0x7D,
            0xBD,
            0xBC,
            0x7C,
            0xB4,
            0x74,
            0x75,
            0xB5,
            0x77,
            0xB7,
            0xB6,
            0x76,
            0x72,
            0xB2,
            0xB3,
            0x73,
            0xB1,
            0x71,
            0x70,
            0xB0,
            0x50,
            0x90,
            0x91,
            0x51,
            0x93,
            0x53,
            0x52,
            0x92,
            0x96,
            0x56,
            0x57,
            0x97,
            0x55,
            0x95,
            0x94,
            0x54,
            0x9C,
            0x5C,
            0x5D,
            0x9D,
            0x5F,
            0x9F,
            0x9E,
            0x5E,
            0x5A,
            0x9A,
            0x9B,
            0x5B,
            0x99,
            0x59,
            0x58,
            0x98,
            0x88,
            0x48,
            0x49,
            0x89,
            0x4B,
            0x8B,
            0x8A,
            0x4A,
            0x4E,
            0x8E,
            0x8F,
            0x4F,
            0x8D,
            0x4D,
            0x4C,
            0x8C,
            0x44,
            0x84,
            0x85,
            0x45,
            0x87,
            0x47,
            0x46,
            0x86,
            0x82,
            0x42,
            0x43,
            0x83,
            0x41,
            0x81,
            0x80,
            0x40,
        ]

        index = 0
        while index < size:
            crc = crcHi ^ data[index]
            crcHi = crcLo ^ crcHiTable[crc]
            crcLo = crcLoTable[crc]
            index += 1

        metCRC16 = (crcHi * 0x0100) + crcLo
        return metCRC16
