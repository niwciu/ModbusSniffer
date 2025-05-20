import serial
from modbus_sniffer.modbus_parser_new import ModbusParser
from modbus_sniffer.csv_logger import CSVLogger


class SerialSnooper:
    def __init__(
        self,
        main_logger,
        port,
        baud=9600,
        parity="none",
        timeout=100,
        raw_log=False,
        raw_only=False,
        csv_log=False,
        daily_file=False,
        data_handler=None,
    ):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.parity = parity
        self.raw_log = raw_log
        self.raw_only = raw_only
        self.log = main_logger
        self.data_handler = data_handler

        # Our new CSV logger (if requested)
        self.csv_logger = (
            CSVLogger(
                enable_csv=csv_log,
                daily_file=daily_file,
                output_dir="./csv_logs",
                base_filename="log",
            )
            if csv_log
            else None
        )

        self.log.info(
            "Opening serial interface: \n"
            + f"\tport: {port}\n"
            + f"\tbaudrate: {baud}\n"
            + "\tbytesize: 8\n"
            + f"\tparity: {parity}\n"
            + "\tstopbits: 1\n"
            + f"\ttimeout: {timeout}s\n"
        )
        self.connection = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=parity,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        self.log.debug(self.connection)

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
            raw_message = " ".join(f"{byte:02x}" for byte in data)
            self.log.info(f"Raw RS485 data: {raw_message}")
            return  # skip decode entirely

        if len(data) <= 0:
            # Check if we have something that might form a valid modbus frame
            if len(self.data) > 2:
                modbus_parser = ModbusParser(
                    self.log,
                    self.csv_logger,
                    self.raw_log,
                    self.trashdata,
                    on_parsed=self.emit_parsed_data,
                )
                self.data = modbus_parser.decodeModbus(self.data)
            return

        # Otherwise, accumulate and decode as normal
        for dat in data:
            self.data.append(dat)

    def emit_parsed_data(self, parsed_data):
        self.log.debug(f"Parsed data ready: {parsed_data}")
        # self.parsed_data_signal.emit(parsed_data) — nie masz tu jeszcze
        # sygnału, ale...
        if self.data_handler:
            self.data_handler(parsed_data)
