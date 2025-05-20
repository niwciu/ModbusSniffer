import pytest
import signal
import sys
from unittest.mock import patch, MagicMock

import modbus_sniffer.cli as cli
from modbus_sniffer.cli import parse_args


def test_parse_args_defaults():
    args = parse_args(["-p", "/dev/ttyUSB0"])
    assert args.port == "/dev/ttyUSB0"
    assert args.baudrate == 9600
    assert args.parity == "even"
    assert args.timeout is None
    assert not args.log_to_file
    assert not args.raw
    assert not args.raw_only
    assert not args.daily_file
    assert not args.csv


def test_parse_args_all_flags():
    args = parse_args(
        [
            "-p",
            "/dev/ttyS1",
            "-b",
            "19200",
            "-r",
            "odd",
            "-t",
            "2",
            "-l",
            "-R",
            "-X",
            "-D",
            "-C",
        ]
    )
    assert args.port == "/dev/ttyS1"
    assert args.baudrate == 19200
    assert args.parity == "odd"
    assert args.timeout == 2
    assert args.log_to_file
    assert args.raw
    assert args.raw_only
    assert args.daily_file
    assert args.csv


def test_parse_args_invalid_parity():
    with pytest.raises(SystemExit):
        parse_args(["-p", "/dev/ttyUSB0", "-r", "invalid"])


def test_signal_handler_exits(monkeypatch):
    exit_mock = MagicMock()
    monkeypatch.setattr(sys, "exit", exit_mock)
    cli.signal_handler(signal.SIGINT, None)
    exit_mock.assert_called_once_with(0)


@patch("modbus_sniffer.cli.configure_logging")
@patch("modbus_sniffer.cli.SerialSnooper")
@patch("modbus_sniffer.cli.normalize_sniffer_config")
@patch("modbus_sniffer.cli.parse_args")
def test_main_happy_path(
    mock_parse_args, mock_normalize, mock_snooper_class, mock_configure_log
):
    mock_args = MagicMock()
    mock_args.port = "COM1"
    mock_args.baudrate = 9600
    mock_args.parity = "even"
    mock_args.timeout = 1
    mock_args.log_to_file = False
    mock_args.raw = False
    mock_args.raw_only = False
    mock_args.daily_file = False
    mock_args.csv = False
    mock_parse_args.return_value = mock_args

    mock_normalize.return_value = {
        "port": "COM1",
        "baudrate": 9600,
        "parity": "even",
        "timeout": 1,
        "log_to_file": False,
        "raw_log": False,
        "raw_only": False,
        "csv_log": False,
        "daily_file": False,
    }

    mock_logger = MagicMock()
    mock_configure_log.return_value = mock_logger

    mock_snooper = MagicMock()
    mock_snooper.read_raw.side_effect = [b"data", KeyboardInterrupt()]
    mock_snooper_class.return_value.__enter__.return_value = mock_snooper

    with patch("sys.exit") as mock_exit:
        cli.main()
        mock_exit.assert_called_once_with(0)
        assert mock_snooper.read_raw.call_count == 2
        mock_snooper.process_data.assert_called_once_with(b"data")
