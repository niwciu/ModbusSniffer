import pytest
from unittest.mock import MagicMock, patch
from modbus_sniffer.gui import SnifferWorker


@patch("modbus_sniffer.gui.configure_logging")
@patch("modbus_sniffer.gui.SerialSnooper")
def test_sniffer_worker_run(mock_snooper_class, mock_configure_logging, qtbot):
    fake_logger = MagicMock()
    mock_configure_logging.return_value = fake_logger

    mock_sniffer = MagicMock()
    mock_snooper_class.return_value.__enter__.return_value = mock_sniffer
    mock_sniffer.read_raw.side_effect = [b"data", b"data2", Exception("End")]

    worker = SnifferWorker(
        port="COM1",
        baudrate=9600,
        parity="none",
        timeout=1000,
        csv_log=False,
        raw_log=False,
        raw_only=False,
        daily_file=False,
        log_to_file=False,
    )
    worker.running = True

    # zastępujemy handler, aby nie emitować sygnałów
    worker.handle_parsed_data = MagicMock()

    worker.run()

    assert mock_sniffer.read_raw.call_count == 3
    fake_logger.error.assert_called_once()
