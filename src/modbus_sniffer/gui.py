from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QStyledItemDelegate,
    QHeaderView,
)
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtSerialPort import QSerialPortInfo
import sys
import platform
from modbus_sniffer.serial_snooper import SerialSnooper
from modbus_sniffer.sniffer_utils import normalize_sniffer_config
from modbus_sniffer.main_logger import configure_logging


class AutoResizeTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setup_table()

    def setup_table(self):
        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        # Resize the column after addind data to table
        self.model().dataChanged.connect(self.resize_columns)

    def resize_columns(self):
        self.resizeColumnsToContents()
        self.resizeRowsToContents()


class AdvancedAlignDelegate(QStyledItemDelegate):
    def __init__(self):
        super().__init__()
        self.column_alignments = {}

    def set_column_alignment(
        self, col, horizontal, vertical=Qt.AlignmentFlag.AlignVCenter
    ):
        self.column_alignments[col] = (horizontal, vertical)

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)

        if index.column() in self.column_alignments:
            h_align, v_align = self.column_alignments[index.column()]
            option.displayAlignment = h_align | v_align


class SnifferWorker(QThread):
    log_signal = pyqtSignal(str)
    parsed_data_signal = pyqtSignal(dict)

    def __init__(
        self,
        port,
        baudrate,
        parity,
        timeout,
        csv_log,
        raw_log,
        raw_only,
        daily_file,
        log_to_file,
    ):
        super().__init__()
        self.port = port
        self.baud = baudrate
        self.parity = parity
        self.timeout = timeout
        self.csv_log = csv_log
        self.raw_log = raw_log
        self.raw_only = raw_only
        self.daily_file = daily_file
        self.log_to_file = log_to_file
        self.running = True
        self.log = configure_logging(
            log_to_file=self.log_to_file,
            daily_file=daily_file,
            gui_callback=self.emit_log,
        )

    def emit_log(self, msg):
        self.log_signal.emit(msg)

    def handle_parsed_data(self, data):
        self.parsed_data_signal.emit(data)

    def run(self):
        try:
            with SerialSnooper(
                main_logger=self.log,
                port=self.port,
                baud=self.baud,
                parity=self.parity,
                timeout=self.timeout,
                raw_log=self.raw_log,
                raw_only=self.raw_only,
                csv_log=self.csv_log,
                daily_file=self.daily_file,
                data_handler=self.handle_parsed_data,
            ) as sniffer:
                while self.running:
                    data = sniffer.read_raw()
                    sniffer.process_data(data)

        except Exception as e:
            self.log.error(f"Exception in sniffer: {str(e)}")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class GUIApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modbus RTU Sniffer GUI")
        self.setGeometry(100, 100, 1400, 800)

        self.last_master = None
        self.last_ok_color = "blue"

        self.pastel_green = "#22F583"
        self.pastel_blue = "#227EF5"
        self.pastel_red = "#FFABAB"
        self.pastel_orange = "#FFD3B6"

        self.layout = QVBoxLayout()
        self.top_layout = QHBoxLayout()

        # ---------- Grid layout for settings ----------
        # Grupa łącząca oba layouty
        self.port_settings_grup = QGroupBox("Settings")

        # Główny layout pionowy wewnątrz grupy
        main_settings_layout = QVBoxLayout()

        # ------- settings_layout: ustawienia portu (poziomo) -------
        self.settings_layout = QHBoxLayout()
        self.settings_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.port_label = QLabel("Port:")
        self.port_input = QComboBox()
        self.port_input.setEditable(True)
        self.port_input.setMinimumWidth(150)

        # def refresh_serial_ports():
        #     self.port_input.clear()
        #     available_ports = QSerialPortInfo.availablePorts()
        #     for port in available_ports:
        #         self.port_input.addItem(port.systemLocation())

        def refresh_serial_ports():
            self.port_input.clear()
            available_ports = QSerialPortInfo.availablePorts()
            for port in available_ports:
                system_location = port.systemLocation()
                if platform.system() == "Windows" and system_location.startswith(
                    "\\\\.\\"
                ):
                    clean_name = system_location.replace("\\\\.\\", "")
                else:
                    clean_name = system_location
                self.port_input.addItem(clean_name)

        self.port_input.showPopup = lambda orig=self.port_input.showPopup: (
            refresh_serial_ports(),
            orig(),
        )[1]

        self.settings_layout.addWidget(
            self.port_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.settings_layout.addWidget(
            self.port_input, alignment=Qt.AlignmentFlag.AlignLeft
        )

        self.baudrate_label = QLabel("Baudrate:")
        self.baudrate_input = QComboBox()
        self.baudrate_input.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.settings_layout.addWidget(
            self.baudrate_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.settings_layout.addWidget(
            self.baudrate_input, alignment=Qt.AlignmentFlag.AlignLeft
        )

        self.parity_label = QLabel("Parity:")
        self.parity_input = QComboBox()
        self.parity_input.addItems(["none", "even", "odd"])
        self.settings_layout.addWidget(
            self.parity_label, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.settings_layout.addWidget(
            self.parity_input, alignment=Qt.AlignmentFlag.AlignLeft
        )

        # ------- timeout_layout --------------------------------------
        self.timeout_layout = QHBoxLayout()
        self.timeout_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.timeout_label = QLabel("Serial Timeout:")
        self.timeout_input = QLineEdit("")
        self.timeout_unit_label = QLabel("ms")
        self.timeout_input.setMaxLength(5)
        self.timeout_input.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.timeout_layout.addWidget(
            self.timeout_label, alignment=Qt.AlignmentFlag.AlignLeft
        )
        self.timeout_layout.addWidget(
            self.timeout_input, alignment=Qt.AlignmentFlag.AlignLeft
        )
        self.timeout_layout.addWidget(
            self.timeout_unit_label, alignment=Qt.AlignmentFlag.AlignLeft
        )

        # ------- options_layout: checkbox ----------------------------
        self.options_layout = QHBoxLayout()
        self.options_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.csv_checkbox = QCheckBox("CSV Log")
        self.raw_checkbox = QCheckBox("Show Raw Message")
        self.raw_only_checkbox = QCheckBox("Raw Data Only")
        self.log_to_file_checkbox = QCheckBox("Log to File")
        self.daily_file_checkbox = QCheckBox("Daily File Rotation")

        font_metrics = QFontMetrics(self.timeout_input.font())
        char_width = font_metrics.horizontalAdvance("0")
        self.timeout_input.setFixedWidth(char_width * 5 + 10)

        self.options_layout.addWidget(
            self.log_to_file_checkbox, alignment=Qt.AlignmentFlag.AlignLeft
        )
        self.options_layout.addWidget(
            self.raw_checkbox, alignment=Qt.AlignmentFlag.AlignLeft
        )
        self.options_layout.addWidget(
            self.raw_only_checkbox, alignment=Qt.AlignmentFlag.AlignLeft
        )
        self.options_layout.addWidget(
            self.csv_checkbox, alignment=Qt.AlignmentFlag.AlignLeft
        )
        self.options_layout.addWidget(
            self.daily_file_checkbox, alignment=Qt.AlignmentFlag.AlignLeft
        )

        # ------- Add all layouts to group -------
        main_settings_layout.addLayout(self.settings_layout)
        main_settings_layout.addLayout(self.timeout_layout)
        main_settings_layout.addLayout(self.options_layout)
        self.port_settings_grup.setLayout(main_settings_layout)

        # Dodaj grupę do głównego layoutu aplikacji
        self.layout.addWidget(self.port_settings_grup)

        # ---------- Start/Stop Buttons ----------
        self.button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.clear_btn = QPushButton("Clear View")
        self.stop_btn.setEnabled(False)
        self.button_layout.addWidget(self.start_btn)
        self.button_layout.addWidget(self.stop_btn)
        self.button_layout.addWidget(self.clear_btn)
        self.layout.addLayout(self.button_layout)

        # ---------- Tabs ----------
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.tabs.addTab(self.tab1, "Logs")
        self.tabs.addTab(self.tab2, "Parsed Data")

        # Tab 1
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.tab1_layout = QVBoxLayout()
        self.tab1_layout.addWidget(self.log_window)
        self.tab1.setLayout(self.tab1_layout)

        # Tab 2
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            [
                "Timestamp",
                "Fn Code",
                "Function name",
                "Msg Type",
                "Slave ID",
                "Data Address",
                "Data Qty",
                "Byte Count",
                "Data",
                "Occurrences",
            ]
        )

        delegate = AdvancedAlignDelegate()
        delegate.set_column_alignment(0, Qt.AlignmentFlag.AlignLeft)
        delegate.set_column_alignment(2, Qt.AlignmentFlag.AlignLeft)
        delegate.set_column_alignment(3, Qt.AlignmentFlag.AlignLeft)
        delegate.set_column_alignment(8, Qt.AlignmentFlag.AlignLeft)
        delegate.set_column_alignment(
            1, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter
        )
        delegate.set_column_alignment(
            4, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter
        )
        delegate.set_column_alignment(
            5, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter
        )
        delegate.set_column_alignment(
            6, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter
        )
        delegate.set_column_alignment(
            7, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter
        )
        delegate.set_column_alignment(
            9, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter
        )
        self.table.setItemDelegate(delegate)

        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        self.table.resizeColumnsToContents()

        self.tab2_layout = QVBoxLayout()
        self.tab2_layout.addWidget(self.table)
        self.tab2.setLayout(self.tab2_layout)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.sniffer_thread = None
        self.data_dict = {}

        # Events
        self.start_btn.clicked.connect(self.start_sniffer)
        self.stop_btn.clicked.connect(self.stop_sniffer)
        self.clear_btn.clicked.connect(self.clear_sniffer_view)

    def start_sniffer(self):
        port = self.port_input.currentText()
        baudrate = int(self.baudrate_input.currentText())
        parity_str = self.parity_input.currentText()
        timeout_input = self.timeout_input.text()
        timeout_input = None if timeout_input == "" else timeout_input
        log_to_file = self.log_to_file_checkbox.isChecked()
        raw = self.raw_checkbox.isChecked()
        raw_only = self.raw_only_checkbox.isChecked()
        daily_file = self.daily_file_checkbox.isChecked()
        csv = self.csv_checkbox.isChecked()

        config = normalize_sniffer_config(
            port=port,
            baudrate=baudrate,
            parity_str=parity_str,
            timeout_input=timeout_input,
            log_to_file=log_to_file,
            raw=raw,
            raw_only=raw_only,
            daily_file=daily_file,
            csv=csv,
            GUI=True,
        )

        self.log_window.append(
            f"<span style='color:yellow'>[INFO] Starting sniffer on "
            f"{config['port']}, {config['baudrate']}, {parity_str}, Timeout: {config['timeout']}</span>"
        )

        self.sniffer_thread = SnifferWorker(**config)
        self.sniffer_thread.log_signal.connect(self.update_log_window)
        self.sniffer_thread.parsed_data_signal.connect(self.update_parsed_data)
        self.sniffer_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_sniffer(self):
        if self.sniffer_thread:
            self.sniffer_thread.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_window.append(
            "<span style='color:yellow'>[INFO] Sniffer stopped.</span>"
        )

    def clear_sniffer_view(self):
        print("cleared")
        self.table.setRowCount(0)
        self.data_dict.clear()

        self.log_window.clear()

        self.last_master = None
        self.last_ok_color = "blue"

    def update_log_window(self, log_entry):
        """
        Update logs in log wiev window.
        Add coloring of the logs
        """
        if "Master" in log_entry:
            if self.last_master == "no response":
                log_entry = f"<span style='color:{self.pastel_red}'>{log_entry}</span>"
            else:
                if self.last_ok_color == "blue":
                    log_entry = f"<span style='color:{self.pastel_green}'>{log_entry}</span>"
                    self.last_ok_color = "green"
                else:
                    log_entry = f"<span style='color:{self.pastel_blue}'>{log_entry}</span>"
                    self.last_ok_color = "blue"
                self.last_master = "no response"
        elif "Slave" in log_entry:
            self.last_master = "answered"
            if self.last_ok_color == "blue":
                log_entry = f"<span style='color:{self.pastel_blue}'>{log_entry}</span>"
            else:
                log_entry = f"<span style='color:{self.pastel_green}'>{log_entry}</span>"
            # add separation after slave log
            log_entry += "<br>"

        # Add log to gui log wiev tab
        self.log_window.append(log_entry)

    def update_parsed_data(self, data):
        if isinstance(data, dict):
            self.add_parsed_data(data)
        elif isinstance(data, list):
            for frame in data:
                self.add_parsed_data(frame)
        else:
            self.log_window.append(
                f"[WARN] Unexpected data type: {type(data)} - {data}"
            )

    def format_table_fields(self, value):
        """
        Formats the address and quantity fields depending on function code and message type.
        Returns (formatted_address, formatted_quantity)
        """
        function = value.get("function")
        message_type = value.get("message_type")

        if function == 23 and message_type == "request":
            try:
                read_addr = int(value["read_address"])
                write_addr = int(value["write_address"])
                read_qty = int(value["read_quantity"])
                write_qty = int(value["write_quantity"])
                formatted_address = f"R: 0x{read_addr:04X} W: 0x{write_addr:04X}"
                formatted_quantity = f"R: {read_qty} W: {write_qty}"
            except (ValueError, TypeError):
                formatted_address = (
                    f"R: {value['read_address']} W: {value['write_address']}"
                )
                formatted_quantity = (
                    f"R: {value['read_quantity']} W: {value['write_quantity']}"
                )
        else:
            # Fallback for other function codes
            data_address = value.get("data_address")
            if data_address is not None and str(data_address).strip():
                try:
                    formatted_address = f"0x{int(data_address):04X}"
                except (ValueError, TypeError):
                    formatted_address = str(data_address)
            else:
                formatted_address = ""

            formatted_quantity = str(value.get("data_qty", ""))

        return formatted_address, formatted_quantity

    def format_data_field(self, value):
        """
        Formats data column (col 8). If 'exception', shows exception code.
        Otherwise formats as list of uint16_t words in hex (big-endian).
        """
        if value.get("function_name") == "exception":
            exception_code = value.get("exception_code")
            if exception_code is not None:
                try:
                    return f"Exception Code: 0x{int(exception_code):02X}"
                except (ValueError, TypeError):
                    return f"Exception Code: {exception_code}"
            else:
                return "Exception Code: Unknown"
        else:
            return ", ".join(f"0x{byte:04X}" for byte in value["data"])

    def add_parsed_data(self, frame):
        key = (
            frame["slave_id"],
            frame["function"],
            frame["data_qty"],
            frame["data_address"],
            frame["message_type"],
            frame["exception_code"],
        )
        timestamp = frame.get("timestamp", "")
        message_type = frame.get("message_type", "")
        data = frame.get("data", [])

        if key in self.data_dict:
            self.data_dict[key]["occurrences"] += 1
            self.data_dict[key]["timestamp"] = timestamp
            self.data_dict[key]["data"] = data
        else:
            self.data_dict[key] = {
                "timestamp": timestamp,
                "message_type": message_type,
                "slave_id": frame["slave_id"],
                "function": frame["function"],
                "function_name": frame["function_name"],
                "data_address": frame["data_address"],
                "data_qty": frame["data_qty"],
                "byte_count": frame["byte_cnt"],
                "data": data,
                "occurrences": 1,
                "exception_code": frame["exception_code"],
                # FC 23 additional fields
                "read_address": frame["read_address"],
                "read_quantity": frame["read_quantity"],
                "write_address": frame["write_address"],
                "write_quantity": frame["write_quantity"],
            }

        self.update_parsed_data_table()

    def update_parsed_data_table(self):
        self.table.setRowCount(0)
        for key, value in self.data_dict.items():
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            # Data adress field formating i case if emty str recived
            # data_address = value.get("data_address")
            # hex_address = ""
            # if data_address is not None and str(data_address).strip():
            #     try:
            #         hex_address = f"0x{int(data_address):04X}"
            #     except (ValueError, TypeError):
            #         hex_address = str(data_address)

            formatted_address, formatted_quantity = self.format_table_fields(value)
            formatted_data = self.format_data_field(value)

            # Adding data to table view
            self.table.setItem(
                row_position, 0, QTableWidgetItem(value["timestamp"].replace("T", " "))
            )
            self.table.setItem(row_position, 3, QTableWidgetItem(value["message_type"]))
            self.table.setItem(
                row_position, 4, QTableWidgetItem(str(value["slave_id"]))
            )
            self.table.setItem(
                row_position, 1, QTableWidgetItem(f"0x{value['function']:02X}")
            )
            self.table.setItem(
                row_position, 2, QTableWidgetItem(value["function_name"])
            )
            self.table.setItem(row_position, 5, QTableWidgetItem(formatted_address))
            self.table.setItem(row_position, 6, QTableWidgetItem(formatted_quantity))
            self.table.setItem(
                row_position, 7, QTableWidgetItem(str(value["byte_count"]))
            )
            self.table.setItem(row_position, 8, QTableWidgetItem(formatted_data))
            self.table.setItem(
                row_position, 9, QTableWidgetItem(str(value["occurrences"]))
            )

        self.table.resizeColumnsToContents()


def main():
    app = QApplication(sys.argv)
    window = GUIApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
