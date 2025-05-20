import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


# --------------------------------------------------------------------------- #
# Custom logging formatter
# --------------------------------------------------------------------------- #
class MyFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            self._style._fmt = "%(asctime)-15s %(message)s"
        elif record.levelno == logging.DEBUG:
            self._style._fmt = (
                "%(asctime)-15s \033[36m%(levelname)-8s\033[0m: %(message)s"
            )
        else:
            color = {
                logging.WARNING: 33,
                logging.ERROR: 31,
                logging.FATAL: 31,
            }.get(record.levelno, 0)
            self._style._fmt = f"%(asctime)-15s \033[{color}m%(levelname)-8s %(threadName)-15s-%(module)-15s:%(lineno)-8s\033[0m: %(message)s"
        return super().format(record)


class GuiLogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        try:
            msg = self.format(record)
            self.callback(msg)
        except Exception:
            self.handleError(record)


def configure_logging(
    log_to_file=True, daily_file=False, gui_callback=None, output_dir="logs"
):
    log = logging.getLogger("global_logger")
    log.setLevel(logging.INFO)

    if log.hasHandlers():
        log.handlers.clear()

    formatter = MyFormatter()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    # GUI handler
    if gui_callback:
        gui_handler = GuiLogHandler(gui_callback)
        gui_handler.setFormatter(formatter)
        log.addHandler(gui_handler)

    # Log to file
    if log_to_file:
        # Determine base directory of the actual app location (not symlink)
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # Combine with output_dir
        logs_dir = os.path.join(base_dir, output_dir)
        os.makedirs(logs_dir, exist_ok=True)

        # Log file name
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"log_{current_time}.log"
        log_file_path = os.path.join(logs_dir, filename)

        if daily_file:
            handler = TimedRotatingFileHandler(
                log_file_path,
                when="midnight",
                interval=1,
                backupCount=7,
                encoding="utf-8",
            )
        else:
            handler = logging.FileHandler(log_file_path, encoding="utf-8")

        handler.setFormatter(formatter)
        log.addHandler(handler)

    return log
