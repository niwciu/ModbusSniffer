import pytest
from modbus_sniffer.gui import GUIApp


@pytest.fixture
def app_instance(qtbot):
    app = GUIApp()
    qtbot.addWidget(app)
    return app


def test_default_state(app_instance):
    assert app_instance.start_btn.isEnabled()
    assert not app_instance.stop_btn.isEnabled()
    assert app_instance.port_input.currentText() == ""


def test_log_window_updates(app_instance, qtbot):
    test_log = "Master: Sending request"
    qtbot.wait(100)
    app_instance.update_log_window(test_log)

    assert "Master" in app_instance.log_window.toPlainText()


def test_add_parsed_data_new_entry(app_instance):
    example_frame = {
        "timestamp": "2024-01-01T12:00:00",
        "function": 3,
        "function_name": "Read Holding Registers",
        "message_type": "response",
        "slave_id": 1,
        "data_address": 100,
        "data_qty": 2,
        "byte_cnt": 4,
        "data": [4660, 22136],
        "exception_code": None,
        "read_address": None,
        "read_quantity": None,
        "write_address": None,
        "write_quantity": None,
    }

    app_instance.add_parsed_data(example_frame)
    assert len(app_instance.data_dict) == 1
    assert app_instance.table.rowCount() == 1
