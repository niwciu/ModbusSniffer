import pytest
import serial
from modbus_sniffer.sniffer_utils import normalize_sniffer_config, calcTimeout


def test_calcTimeout_low_baudrate():
    assert abs(calcTimeout(9600) - (36 / 9600)) < 1e-6
    assert abs(calcTimeout(19200) - 0.001850) < 1e-6  # test boundary condition


def test_calcTimeout_high_baudrate():
    assert calcTimeout(20000) == 0.001850
    assert calcTimeout(115200) == 0.001850


@pytest.mark.parametrize(
    "parity_str, expected_parity",
    [
        ("none", serial.PARITY_NONE),
        ("even", serial.PARITY_EVEN),
        ("odd", serial.PARITY_ODD),
        ("invalid", serial.PARITY_ODD),  # default to odd if not none/even
    ],
)
def test_parity_mapping(parity_str, expected_parity):
    config = normalize_sniffer_config(
        port="COM1",
        baudrate=9600,
        parity_str=parity_str,
        timeout_input=None,
        log_to_file=False,
        raw=False,
        raw_only=False,
        daily_file=False,
        csv=False,
        GUI=False,
    )
    assert config["parity"] == expected_parity


def test_timeout_input_overrides_calcTimeout():
    # timeout_input given in ms, converted to seconds
    config = normalize_sniffer_config(
        port="COM1",
        baudrate=9600,
        parity_str="none",
        timeout_input=500,  # 500 ms
        log_to_file=False,
        raw=False,
        raw_only=False,
        daily_file=False,
        csv=False,
        GUI=False,
    )
    assert config["timeout"] == 0.5


def test_log_to_file_for_raw_and_raw_only_without_gui():
    # raw=True should force log_to_file=True if GUI=False
    config = normalize_sniffer_config(
        port="COM1",
        baudrate=9600,
        parity_str="none",
        timeout_input=None,
        log_to_file=False,
        raw=True,
        raw_only=False,
        daily_file=False,
        csv=False,
        GUI=False,
    )
    assert config["log_to_file"] is True

    # raw_only=True should force log_to_file=True if GUI=False
    config = normalize_sniffer_config(
        port="COM1",
        baudrate=9600,
        parity_str="none",
        timeout_input=None,
        log_to_file=False,
        raw=False,
        raw_only=True,
        daily_file=False,
        csv=False,
        GUI=False,
    )
    assert config["log_to_file"] is True


def test_log_to_file_not_for_raw_with_gui():
    config = normalize_sniffer_config(
        port="COM1",
        baudrate=9600,
        parity_str="none",
        timeout_input=None,
        log_to_file=False,
        raw=True,
        raw_only=False,
        daily_file=False,
        csv=False,
        GUI=True,
    )
    assert config["log_to_file"] is False


def test_daily_file_for_csv_enabled():
    # csv True forces daily_file True
    config = normalize_sniffer_config(
        port="COM1",
        baudrate=9600,
        parity_str="none",
        timeout_input=None,
        log_to_file=False,
        raw=False,
        raw_only=False,
        daily_file=False,
        csv=True,
        GUI=False,
    )
    assert config["daily_file"] is True


def test_returned_dict_keys_and_types():
    config = normalize_sniffer_config(
        port="/dev/ttyUSB0",
        baudrate=19200,
        parity_str="even",
        timeout_input=None,
        log_to_file=True,
        raw=False,
        raw_only=False,
        daily_file=False,
        csv=False,
        GUI=False,
    )

    keys = {
        "port": str,
        "baudrate": int,
        "parity": str,
        "timeout": float,
        "raw_log": bool,
        "raw_only": bool,
        "csv_log": bool,
        "daily_file": bool,
        "log_to_file": bool,
    }

    for key, expected_type in keys.items():
        assert key in config
        assert isinstance(config[key], expected_type)
