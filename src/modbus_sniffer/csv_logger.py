import os
import csv
from datetime import datetime


class CSVLogger:
    def __init__(
        self,
        enable_csv=False,
        daily_file=False,
        output_dir=".",
        base_filename="modbus_data",
    ):
        self.enable_csv = enable_csv
        self.daily_file = daily_file
        self.output_dir = output_dir
        self.base_filename = base_filename

        self.register_map = {}
        self.columns = ["Timestamp", "Slave ID", "Operation"]
        self.csv_file = None
        self.csv_writer = None
        self.current_date_str = None

        if self.enable_csv:
            self._open_csv_file()

    def _get_date_str(self):
        return datetime.now().strftime("%Y%m%d")

    def _get_datetime_str(self):
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def _open_csv_file(self):
        if self.csv_file:
            self.csv_file.close()

        date_time_str = self._get_datetime_str()
        filename = f"{self.base_filename}_{date_time_str}.csv"

        os.makedirs(self.output_dir, exist_ok=True)
        fullpath = os.path.join(self.output_dir, filename)

        self.csv_file = open(fullpath, mode="w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(self.columns)
        self.csv_file.flush()

        if self.daily_file:
            self.current_date_str = self._get_date_str()

    def _check_daily_rotation(self):
        if not self.daily_file:
            return
        current = self._get_date_str()
        if current != self.current_date_str:
            self._open_csv_file()

    def _expand_header_for_registers(self, slave_id, start_register, quantity):
        changed = False
        for offset in range(quantity):
            reg_addr = start_register + offset
            key = (slave_id, reg_addr)
            if key not in self.register_map:
                new_col_name = f"Reg_{slave_id}_{reg_addr}"
                self.columns.append(new_col_name)
                self.register_map[key] = len(self.columns) - 1
                changed = True

        if changed:
            self._rewrite_file_with_new_header()

    def _rewrite_file_with_new_header(self):
        if not self.csv_file:
            return

        self.csv_file.close()
        old_path = self.csv_file.name

        with open(old_path, mode="r", encoding="utf-8") as f:
            reader = list(csv.reader(f))

        old_header = reader[0] if reader else []
        old_rows = reader[1:] if len(reader) > 1 else []

        with open(old_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.columns)

            old_col_map = {col_name: idx for idx, col_name in enumerate(old_header)}

            for old_row in old_rows:
                new_row = [""] * len(self.columns)
                for col_index, col_name in enumerate(old_header):
                    if col_index < len(old_row):
                        cell_value = old_row[col_index]
                    else:
                        cell_value = ""
                    if col_name in old_col_map and col_name in self.columns:
                        new_index = self.columns.index(col_name)
                        new_row[new_index] = cell_value
                writer.writerow(new_row)

        self.csv_file = open(old_path, mode="a", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)

    def log_data(
        self, timestamp, slave_id, operation, start_register, quantity, register_values
    ):
        if not self.enable_csv:
            return

        self._check_daily_rotation()
        self._expand_header_for_registers(slave_id, start_register, quantity)

        row = [""] * len(self.columns)
        row[0] = timestamp
        row[1] = slave_id
        row[2] = operation

        for i, val in enumerate(register_values):
            reg_addr = start_register + i
            col_idx = self.register_map.get((slave_id, reg_addr), None)
            if col_idx is not None:
                row[col_idx] = val

        self.csv_writer.writerow(row)
        self.csv_file.flush()

    def close(self):
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
