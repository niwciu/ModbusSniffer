import logging
import os
import sys
import tempfile

from modbus_sniffer.main_logger import (
    configure_logging,
    GuiLogHandler,
    MyFormatter,
)


def test_formatter_formats_correctly():
    formatter = MyFormatter()
    record_info = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="info msg",
        args=(),
        exc_info=None,
    )
    record_debug = logging.LogRecord(
        name="test",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="debug msg",
        args=(),
        exc_info=None,
    )
    record_warn = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="warn msg",
        args=(),
        exc_info=None,
    )

    info_formatted = formatter.format(record_info)
    debug_formatted = formatter.format(record_debug)
    warn_formatted = formatter.format(record_warn)

    assert "info msg" in info_formatted
    assert "\033[36mDEBUG" in debug_formatted  # kolor cyan dla DEBUG
    assert "\033[33mWARNING" in warn_formatted  # kolor żółty dla WARNING


def test_gui_log_handler_calls_callback():
    called_messages = []

    def dummy_callback(msg):
        called_messages.append(msg)

    handler = GuiLogHandler(dummy_callback)
    formatter = MyFormatter()
    handler.setFormatter(formatter)

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test message",
        args=(),
        exc_info=None,
    )
    handler.emit(record)

    assert len(called_messages) == 1
    assert "test message" in called_messages[0]


def test_configure_logging_creates_handlers(tmp_path):
    # Patch sys.executable and __file__ to control base_dir behavior
    original_frozen = getattr(sys, "frozen", False)
    original_executable = getattr(sys, "executable", None)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate non-frozen environment (__file__ points to tmp_path)
            if hasattr(sys, "frozen"):
                delattr(sys, "frozen")
            sys.executable = "/some/path/python"

            # Temporarily patch __file__ to tmp_path for base_dir detection
            module = sys.modules[__name__]
            old_file = getattr(module, "__file__", None)
            setattr(module, "__file__", str(tmp_path / "dummy.py"))

            log = configure_logging(
                log_to_file=True, daily_file=False, gui_callback=None, output_dir=tmpdir
            )

            # Logger should have at least console and file handler
            handlers = log.handlers
            assert any(isinstance(h, logging.StreamHandler) for h in handlers)
            assert any(isinstance(h, logging.FileHandler) for h in handlers)

            # Check if log file is created
            log_file_handlers = [
                h for h in handlers if isinstance(h, logging.FileHandler)
            ]
            assert log_file_handlers
            file_path = log_file_handlers[0].baseFilename
            assert os.path.exists(file_path)

    finally:
        # Restore
        if original_frozen:
            setattr(sys, "frozen", original_frozen)
        else:
            if hasattr(sys, "frozen"):
                delattr(sys, "frozen")
        if original_executable is not None:
            sys.executable = original_executable
        if old_file is not None:
            setattr(module, "__file__", old_file)


def test_configure_logging_with_gui_callback():
    with tempfile.TemporaryDirectory() as tmpdir:
        called_messages = []

        def gui_callback(msg):
            called_messages.append(msg)

        log = configure_logging(
            log_to_file=False, gui_callback=gui_callback, output_dir=tmpdir
        )

        log.info("test gui log")
        assert any("test gui log" in msg for msg in called_messages)


def test_daily_file_handler_is_timed_rotating_file_handler(tmp_path):
    # Patch __file__ to tmp_path
    module = sys.modules[__name__]
    old_file = getattr(module, "__file__", None)
    setattr(module, "__file__", str(tmp_path / "dummy.py"))

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            log = configure_logging(
                log_to_file=True, daily_file=True, output_dir=tmpdir
            )
            handlers = log.handlers
            timed_handlers = [
                h
                for h in handlers
                if isinstance(h, logging.handlers.TimedRotatingFileHandler)
            ]
            assert timed_handlers
    finally:
        if old_file is not None:
            setattr(module, "__file__", old_file)
