from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox, QGroupBox, QPushButton, QTextEdit, QTabWidget, QTableWidget, QTableWidgetItem, QStyledItemDelegate, QHeaderView
import sys
from module.serial_snooper import SerialSnooper
from module.sniffer_utils import normalize_sniffer_config, calcTimeout
from module.main_logger import configure_logging

class AutoResizeTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setup_table()
        
    def setup_table(self):
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Wywołaj resize po dodaniu danych
        self.model().dataChanged.connect(self.resize_columns)
        
    def resize_columns(self):
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
class AdvancedAlignDelegate(QStyledItemDelegate):
    def __init__(self):
        super().__init__()
        self.column_alignments = {}  # Przechowuje reguły dla kolumn {indeks: (poziome, pionowe)}

    def set_column_alignment(self, col, horizontal, vertical=Qt.AlignmentFlag.AlignVCenter):
        self.column_alignments[col] = (horizontal, vertical)

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        
        if index.column() in self.column_alignments:
            h_align, v_align = self.column_alignments[index.column()]
            option.displayAlignment = h_align | v_align  # Łączenie flag


# Klasa do pracy z wątkami - odpowiada za sniffera
class SnifferWorker(QThread):
    log_signal = pyqtSignal(str)
    parsed_data_signal = pyqtSignal(dict)

    def __init__(self, port, baudrate, parity, timeout, csv_log, raw_log, raw_only, daily_file, log_to_file):
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
        self.log = configure_logging(log_to_file=self.log_to_file, daily_file=daily_file, gui_callback=self.emit_log)

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
                data_handler=self.handle_parsed_data
            ) as sniffer:
                while self.running:
                    data = sniffer.read_raw()
                    parsed_data = sniffer.process_data(data)
                    
        except Exception as e:
            self.log.error(f"Exception in sniffer: {str(e)}")




    def stop(self):
        self.running = False
        self.quit()
        self.wait()



# Główna aplikacja GUI
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

        # UI komponenty
        self.port_label = QLabel("Port:")
        self.port_input = QLineEdit("/dev/ttyUSB0")
        self.top_layout.addWidget(self.port_label)
        self.top_layout.addWidget(self.port_input)

        self.baud_label = QLabel("Baudrate:")
        self.baud_input = QLineEdit("115200")
        self.top_layout.addWidget(self.baud_label)
        self.top_layout.addWidget(self.baud_input)

        self.parity_label = QLabel("Parity:")
        self.parity_input = QComboBox()
        self.parity_input.addItems(["none", "even", "odd"])
        self.top_layout.addWidget(self.parity_label)
        self.top_layout.addWidget(self.parity_input)

        self.layout.addLayout(self.top_layout)

        # Timeout Input
        self.timeout_label = QLabel("Timeout (seconds):")
        self.timeout_input = QLineEdit("None")
        self.top_layout.addWidget(self.timeout_label)
        self.top_layout.addWidget(self.timeout_input)

        # Opcje
        self.options_group = QGroupBox("Options")
        self.options_layout = QHBoxLayout()

        self.csv_checkbox = QCheckBox("CSV Log")
        self.raw_checkbox = QCheckBox("Show Raw Message")
        self.raw_only_checkbox = QCheckBox("Raw Data Only")
        self.log_to_file_checkbox = QCheckBox("Log to File")
        self.daily_file_checkbox = QCheckBox("Daily File Rotation")
        
        self.options_layout.addWidget(self.csv_checkbox)
        self.options_layout.addWidget(self.raw_checkbox)
        self.options_layout.addWidget(self.raw_only_checkbox)
        self.options_layout.addWidget(self.log_to_file_checkbox)
        self.options_layout.addWidget(self.daily_file_checkbox)

        self.options_group.setLayout(self.options_layout)
        self.layout.addWidget(self.options_group)

        self.button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.button_layout.addWidget(self.start_btn)
        self.button_layout.addWidget(self.stop_btn)
        self.layout.addLayout(self.button_layout)

        # Zakładki
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.tabs.addTab(self.tab1, "Logs")
        self.tabs.addTab(self.tab2, "Parsed Data")

        # Zakładka 1: Logi
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.tab1_layout = QVBoxLayout()
        self.tab1_layout.addWidget(self.log_window)
        self.tab1.setLayout(self.tab1_layout)

        # Zakładka 2: Tabela z danymi
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Fn Code","Function name","Msg Type", "Slave ID", "Data Address", "Data Qty", "Byte Count", "Data", "Occurrences"
        ])
        # Wyśrodkowanie przez delegata
        delegate = AdvancedAlignDelegate()

        # Kolumna 0: do lewej + pionowo na środku (domyślne)
        delegate.set_column_alignment(0, Qt.AlignmentFlag.AlignLeft) 
        delegate.set_column_alignment(2, Qt.AlignmentFlag.AlignLeft) 
        delegate.set_column_alignment(3, Qt.AlignmentFlag.AlignLeft)
        delegate.set_column_alignment(8, Qt.AlignmentFlag.AlignLeft) 
        # Kolumna 1: do prawej + pionowo na środku
        # delegate.set_column_alignment(3, Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignVCenter)
        # Kolumna 2: wyśrodkowane w obu kierunkach
        delegate.set_column_alignment(4, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter)
        delegate.set_column_alignment(1, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter)
        delegate.set_column_alignment(5, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter)
        delegate.set_column_alignment(6, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter)
        delegate.set_column_alignment(7, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter)
        delegate.set_column_alignment(9, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter)
        self.table.setItemDelegate(delegate)
                             
        # Wyśrodkowanie tekstu w nagłówkach
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        # Ustaw auto-resize
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)       
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)    
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)        
        # Autodopasowanie szerokości kolumn do zawartości
        self.table.resizeColumnsToContents()

        self.tab2_layout = QVBoxLayout()
        self.tab2_layout.addWidget(self.table)
        self.tab2.setLayout(self.tab2_layout)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.sniffer_thread = None
        self.data_dict = {}  # Słownik do przechowywania sparsowanych danych

        # Zdarzenia
        self.start_btn.clicked.connect(self.start_sniffer)
        self.stop_btn.clicked.connect(self.stop_sniffer)

    def start_sniffer(self):
        # Uruchomienie sniffera
        port = self.port_input.text()
        baudrate = int(self.baud_input.text())
        parity_str = self.parity_input.currentText()
        timeout_input = self.timeout_input.text()

        timeout_input = None if timeout_input.strip().lower() == "none" else timeout_input

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
            csv=csv
        )

        self.log_window.append(f"<span style='color:yellow'>[INFO] Starting sniffer on {config['port']}, {config['baudrate']}, {parity_str}, Timeout: {config['timeout']}</span>")

        self.sniffer_thread = SnifferWorker(**config)
        self.sniffer_thread.log_signal.connect(self.update_log_window)
        self.sniffer_thread.parsed_data_signal.connect(self.update_parsed_data)
        self.sniffer_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_sniffer(self):
        # Zatrzymanie sniffera
        if self.sniffer_thread:
            self.sniffer_thread.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_window.append("<span style='color:yellow'>[INFO] Sniffer stopped.</span>")

    def update_log_window(self, log_entry):
        """
        Aktualizacja logów w oknie.
        Dodaje kolorowanie na podstawie par Master/Slave.
        """

        # Sprawdzamy, czy to jest log dla Master
        if "Master" in log_entry:
            # Master ma odpowiedź, więc kolorujemy go na zielono
            if self.last_master == "no response":  # Jeśli poprzedni Master nie miał odpowiedzi
                log_entry = f"<span style='color:{self.pastel_red}'>{log_entry}</span>"
            else:
                if self.last_ok_color == "blue":
                    log_entry = f"<span style='color:{self.pastel_green}'>{log_entry}</span>"
                    self.last_ok_color = "green"
                else:
                    log_entry = f"<span style='color:{self.pastel_blue}'>{log_entry}</span>"
                    self.last_ok_color = "blue"
                self.last_master = "no response"

        # Sprawdzamy, czy to jest log dla Slave
        elif "Slave" in log_entry:
            self.last_master = "answered"  # Zapamiętujemy, że ten Master miał odpowiedź
            if self.last_ok_color == "blue":
                log_entry = f"<span style='color:{self.pastel_blue}'>{log_entry}</span>"
            else:
                log_entry = f"<span style='color:{self.pastel_green}'>{log_entry}</span>"

            # Dodajemy pustą linię po logu Slave
            log_entry += "<br>"

        # Wstawiamy log do GUI
        self.log_window.append(log_entry)


    def update_parsed_data(self, data):
        # Obsługa sytuacji, gdy przesłany jest pojedynczy dict
        if isinstance(data, dict):
            self.add_parsed_data(data)
        elif isinstance(data, list):
            for frame in data:
                self.add_parsed_data(frame)
        else:
            self.log_window.append(f"[WARN] Nieoczekiwany typ danych: {type(data)} - {data}")


    def add_parsed_data(self, frame):
        """Dodanie danych do tabeli (request/response merge)"""
        key = (frame['slave_id'], frame['function'], frame['data_qty'],frame ['message_type'])
        timestamp = frame.get('timestamp', '')
        message_type = frame.get('message_type', '')
        data = frame.get('data', [])
        
        # Aktualizacja danych w słowniku
        if key in self.data_dict:
            self.data_dict[key]["occurrences"] += 1
            self.data_dict[key]["timestamp"] = timestamp  # Zaktualizowanie timestampu
            self.data_dict[key]["data"] = data  # Zaktualizowanie timestampu
        else:
            self.data_dict[key] = {
                "timestamp": timestamp,
                "message_type": message_type,
                "slave_id": frame['slave_id'],
                "function": frame['function'],
                "function_name": frame['function_name'],
                "data_address": frame['data_address'],
                "data_qty": frame['data_qty'],
                "byte_count": frame['byte_cnt'],
                "data": data,
                "occurrences": 1
            }

        self.update_parsed_data_table()

    def update_parsed_data_table(self):
        """Zaktualizowanie tabeli na podstawie słownika danych"""
        self.table.setRowCount(0)  # Wyczyszczenie tabeli
        for key, value in self.data_dict.items():
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            # Bezpieczne formatowanie data_address
            data_address = value.get("data_address")
            hex_address = ""
            if data_address is not None and str(data_address).strip():
                try:
                    hex_address = f"0x{int(data_address):04X}"
                except (ValueError, TypeError):
                    hex_address = str(data_address)

            # Wstawianie danych do tabeli
            self.table.setItem(row_position, 0, QTableWidgetItem(value["timestamp"].replace("T", " ")))
            self.table.setItem(row_position, 3, QTableWidgetItem(value["message_type"]))
            self.table.setItem(row_position, 4, QTableWidgetItem(str(value["slave_id"])))
            self.table.setItem(row_position, 1, QTableWidgetItem(f"0x{value['function']:02X}"))
            self.table.setItem(row_position, 2, QTableWidgetItem(value["function_name"]))
            self.table.setItem(row_position, 5, QTableWidgetItem(hex_address))  
            self.table.setItem(row_position, 6, QTableWidgetItem(str(value["data_qty"])))
            self.table.setItem(row_position, 7, QTableWidgetItem(str(value["byte_count"])))
            self.table.setItem(row_position, 8, QTableWidgetItem(", ".join(f"0x{byte:02X}" for byte in value["data"])))
            self.table.setItem(row_position, 9, QTableWidgetItem(str(value["occurrences"])))
            
        self.table.resizeColumnsToContents()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GUIApp()
    window.show()
    sys.exit(app.exec())
