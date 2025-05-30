import pytest
from modbus_sniffer.modbus_parser_new import ModbusParser


# @pytest.fixture
# def parser():
#     main_logger = DummyLogger()
#     csv_logger = DummyCSVLogger()
#     parsed_frames = []
#     def on_parsed(frame):
#         parsed_frames.append(frame)
#     parser = ModbusParser(
#         main_logger=main_logger,
#         csv_logger=csv_logger,
#         raw_log=True,
#         trashdata=True,
#         on_parsed=on_parsed
#     )
#     parser._parsed_frames = parsed_frames  # żeby mieć dostęp do zdekodowanych ramek
#     parser._main_logger = main_logger
#     parser._csv_logger = csv_logger
#     return parser

# def test_calc_crc16_known_value(parser):
#     data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01])
#     crc = parser.calcCRC16(data, len(data))
#     assert crc == 0x840A

# def test_decode_valid_read_registers_request(parser):
#     # Frame: slave=1, fc=3, addr=0x0000, qty=0x0001, CRC=0x840A
#     frame = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])
#     result = parser.decodeModbus(frame)
#     assert len(parser._parsed_frames) == 1
#     parsed = parser._parsed_frames[0]
#     assert parsed['slave_id'] == 1
#     assert parsed['function'] == 3
#     assert parsed['data_address'] == 0
#     assert parsed['data_qty'] == 1
#     # assert result == True

# def test_decode_invalid_crc_returns_false(parser):
#     frame = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00])  # złe CRC
#     result = parser.decodeModbus(frame)
#     assert result is False
#     assert len(parser._parsed_frames) == 0

# def test_decode_unknown_function_logs_info(parser):
#     # Funkcja 0x99 nieznana
#     frame = bytes([0x01, 0x99, 0x00, 0x00, 0x84, 0x09])
#     result = parser.decodeModbus(frame)
#     assert result is False
#     # Sprawdzamy, czy w loggerze jest info o nieznanej funkcji
#     found = any("Unknown function" in msg for msg in parser._main_logger.messages)
#     assert found

# def test_decode_garbage_data_returns_false(parser):
#     frame = b"randomgarbage"
#     result = parser.decodeModbus(frame)
#     assert result is False
#     assert len(parser._parsed_frames) == 0
import pytest
from unittest.mock import Mock
from datetime import datetime

# Import your class
# from your_module import ModbusParser


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg):
        self.messages.append(msg)


class DummyCSVLogger:
    def __init__(self):
        self.logged = []

    def log_data(self, timestamp, sid, op, addr, qty, values):
        self.logged.append((timestamp, sid, op, addr, qty, values))


@pytest.fixture
def setup_parser():
    main_logger = Mock()
    csv_logger = DummyCSVLogger()
    on_parsed = Mock()
    parser = ModbusParser(
        main_logger, csv_logger, raw_log=True, trashdata=False, on_parsed=on_parsed
    )
    return parser, main_logger, csv_logger, on_parsed


def build_frame(data_bytes):
    # Helper: append correct CRC to data_bytes
    parser = ModbusParser(Mock(), None)
    crc = parser.calcCRC16(data_bytes, len(data_bytes))
    crc_hi = (crc >> 8) & 0xFF
    crc_lo = crc & 0xFF
    return data_bytes + bytes([crc_hi, crc_lo])


def test_read_registers_request_and_response(setup_parser):
    parser, log, csv, on_parsed = setup_parser

    # Make sure csvlog attribute is set correctly if needed:
    # parser.csvlog = csv  # just to be safe

    # Build Read Holding Registers request
    req = bytes([1, 3, 0x00, 0x0A, 0x00, 0x02])
    req = build_frame(req)
    leftover = parser.decodeModbus(req)
    assert leftover == b""
    on_parsed.assert_called_once()
    frame = on_parsed.call_args[0][0]
    assert frame["slave_id"] == 1
    assert frame["function"] == 3
    assert frame["data_address"] == 10
    assert frame["data_qty"] == 2
    assert frame["message_type"] == "request"
    assert frame["direction"] == "master"

    # Response frame
    resp = bytes([1, 3, 4, 0x00, 0x01, 0x00, 0x02])
    resp = build_frame(resp)
    leftover = parser.decodeModbus(resp)
    assert leftover == b""
    assert on_parsed.call_count == 2
    resp_frame = on_parsed.call_args[0][0]
    assert resp_frame["slave_id"] == 1
    assert resp_frame["function"] == 3
    assert resp_frame["message_type"] == "response"
    assert resp_frame["direction"] == "slave"
    assert resp_frame["data"] == [1, 2]

    # CSV logger should have logged exactly once
    assert len(csv.logged) == 1


def test_write_single_register_request_and_response(setup_parser):
    parser, log, csv, on_parsed = setup_parser

    # Write Single Register request: Slave ID=1, FC=6, Addr=0x0005,
    # Value=0x00FF
    req = bytes([1, 6, 0x00, 0x05, 0x00, 0xFF])
    req = build_frame(req)
    leftover = parser.decodeModbus(req)
    assert leftover == b""
    frame = on_parsed.call_args[0][0]
    assert frame["function"] == 6
    assert frame["data_address"] == 5
    assert frame["data"] == [0x00, 0xFF]
    assert frame["message_type"] == "request"

    # Write Single Register response (echo)
    resp = bytes([1, 6, 0x00, 0x05, 0x00, 0xFF])
    resp = build_frame(resp)
    leftover = parser.decodeModbus(resp)
    assert leftover == b""
    resp_frame = on_parsed.call_args[0][0]
    assert resp_frame["function"] == 6
    assert resp_frame["message_type"] == "response"
    assert resp_frame["data_address"] == 5
    assert resp_frame["data"] == [0x00, 0xFF]

    # CSV log should contain one write record
    assert len(csv.logged) == 1
    _, sid, op, addr, qty, values = csv.logged[0]
    assert op == "WRITE"
    assert addr == 5
    assert qty == 1
    assert values == [255]


def test_handle_exception_response(setup_parser):
    parser, log, csv, on_parsed = setup_parser

    # Exception response: Slave ID=1, FC=0x83 (FC=3 + error mask), Exception
    # code=2
    data = bytes([1, 0x83, 2])
    data = build_frame(data)
    leftover = parser.decodeModbus(data)
    assert leftover == b""
    frame = on_parsed.call_args[0][0]
    assert frame["function"] == 0x83
    assert frame["exception_code"] == 2
    assert frame["message_type"] == "response"
    assert frame["direction"] == "slave"


def test_trash_data_handling(setup_parser):
    parser, log, csv, on_parsed = setup_parser

    # Send invalid frame (just random bytes)
    garbage = b"\x99\x88\x77\x66"
    leftover = parser.decodeModbus(garbage)

    # Should not crash
    assert isinstance(leftover, bytes)

    # Leftover może być pusty lub zawierać fragment, ale nie może zawierać nic
    # poza przekazanymi bajtami
    assert all(b in garbage for b in leftover)

    # (opcjonalnie) jeśli chcesz, żeby leftover był krótszy lub równy od garbage
    assert len(leftover) <= len(garbage)


def test_pending_requests_logic(setup_parser):
    parser, log, csv, on_parsed = setup_parser

    # Send request for Read Holding Registers FC=3
    req = bytes([1, 3, 0x00, 0x01, 0x00, 0x01])
    req = build_frame(req)
    leftover = parser.decodeModbus(req)
    assert leftover == b""
    assert (1, 3) in parser.pendingRequests

    # Send response for same (removes pending)
    resp = bytes([1, 3, 2, 0x00, 0x01])
    resp = build_frame(resp)
    leftover = parser.decodeModbus(resp)
    assert leftover == b""
    assert (1, 3) not in parser.pendingRequests


def test_read_write_multiple_registers_request_and_response(setup_parser):
    parser, log, csv, on_parsed = setup_parser

    # Build FC=23 request
    # Slave ID=1, FC=23,
    # ReadAddr=0x000A, ReadQty=2,
    # WriteAddr=0x0010, WriteQty=2,
    # ByteCount=4, Data=0x0001, 0x0002
    req_data = bytes(
        [
            1,
            23,
            0x00,
            0x0A,
            0x00,
            0x02,
            0x00,
            0x10,
            0x00,
            0x02,
            4,
            0x00,
            0x01,
            0x00,
            0x02,
        ]
    )
    req = build_frame(req_data)
    leftover = parser.decodeModbus(req)
    assert leftover == b""
    frame = on_parsed.call_args[0][0]
    assert frame["function"] == 23
    assert frame["read_address"] == 10
    assert frame["read_quantity"] == 2
    assert frame["write_address"] == 16
    assert frame["write_quantity"] == 2
    assert frame["message_type"] == "request"

    # Response: Slave ID=1, FC=23, ByteCount=4, Data=0x0001 0x0002
    resp_data = bytes([1, 23, 4, 0x00, 0x01, 0x00, 0x02])
    resp = build_frame(resp_data)
    leftover = parser.decodeModbus(resp)
    assert leftover == b""
    resp_frame = on_parsed.call_args[0][0]
    assert resp_frame["function"] == 23
    assert resp_frame["message_type"] == "response"
    assert resp_frame["data"] == [1, 2]
