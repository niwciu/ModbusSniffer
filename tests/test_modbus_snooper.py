from unittest.mock import MagicMock, patch
from modbus_sniffer.serial_snooper import SerialSnooper


@patch("modbus_sniffer.serial_snooper.serial.Serial")
def test_serial_snooper_read_and_process(mock_serial):
    serial_instance = MagicMock()
    serial_instance.read.return_value = (
        b"\x01\x03\x02\x00\x0a\x79\x84"  # example modbus frame
    )
    mock_serial.return_value = serial_instance

    logger = MagicMock()

    snooper = SerialSnooper(
        main_logger=logger,
        port="/dev/null",
        baud=9600,
        parity="E",
        timeout=1,
        raw_log=False,
        raw_only=False,
        csv_log=False,
        daily_file=False,
    )

    with snooper:
        data = snooper.read_raw()
        assert data == b"\x01\x03\x02\x00\x0a\x79\x84"
        snooper.process_data(data)

    logger.info.assert_called()  # at least one logging call
