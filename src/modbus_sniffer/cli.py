"""
Python modbus sniffer implementation
---------------------------------------------------------------------------

The following is a modbus RTU sniffer program,
made without the use of any modbus-specific library.
"""

import argparse
import signal
import sys
from modbus_sniffer.sniffer_utils import normalize_sniffer_config
from modbus_sniffer.serial_snooper import SerialSnooper
from modbus_sniffer.main_logger import configure_logging


def signal_handler(sig, frame):
    print("\nGoodbye\n")
    sys.exit(0)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Modbus RTU sniffer that logs decoded frames and optionally raw data."
    )
    parser.add_argument(
        "-p",
        "--port",
        required=True,
        help="Select the serial port (e.g. COM3, /dev/ttyUSB0).",
    )
    parser.add_argument(
        "-b",
        "--baudrate",
        type=int,
        default=9600,
        help="Set the communication baud rate (default: 9600).",
    )
    parser.add_argument(
        "-r",
        "--parity",
        default="even",
        choices=["none", "even", "odd"],
        help="Select parity: none, even, or odd (default: even).",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=None,
        help="Inter-frame timeout in seconds. If not set, an automatic calculation is used.",
    )
    parser.add_argument(
        "-l",
        "--log-to-file",
        action="store_true",
        default=False,
        help="Write console log to a file as well (default: False).",
    )
    parser.add_argument(
        "-R",
        "--raw",
        action="store_true",
        default=False,
        help="Additional logging of raw messages in hex. (implies --log-to-file for CLI app)",
    )
    parser.add_argument(
        "-X",
        "--raw-only",
        action="store_true",
        default=False,
        help="Log only raw traffic in hex, skip decode (implies --log-to-file for CLI app).",
    )
    parser.add_argument(
        "-D",
        "--daily-file",
        action="store_true",
        default=False,
        help="Rotate logs daily at midnight (default: False).",
    )
    parser.add_argument(
        "-C",
        "--csv",
        action="store_true",
        default=False,
        help="Log decoded register data to a CSV file (implies daily rotation).",
    )

    return parser.parse_args(argv)


def main():
    # Initialize Ctrl+C handler
    signal.signal(signal.SIGINT, signal_handler)

    args = parse_args()

    sniffer_config = normalize_sniffer_config(
        port=args.port,
        baudrate=args.baudrate,
        parity_str=args.parity,
        timeout_input=args.timeout,
        log_to_file=args.log_to_file or args.raw or args.raw_only,
        raw=args.raw,
        raw_only=args.raw_only,
        daily_file=args.daily_file,
        csv=args.csv,
    )

    log = configure_logging(
        log_to_file=sniffer_config["log_to_file"],
        daily_file=sniffer_config["daily_file"],
        output_dir="./logs",
    )

    try:
        with SerialSnooper(
            main_logger=log,
            port=sniffer_config["port"],
            baud=sniffer_config["baudrate"],
            parity=sniffer_config["parity"],
            timeout=sniffer_config["timeout"],
            raw_log=sniffer_config["raw_log"],
            raw_only=sniffer_config["raw_only"],
            csv_log=sniffer_config["csv_log"],
            daily_file=sniffer_config["daily_file"],
        ) as sniffer:
            while True:
                data = sniffer.read_raw()
                sniffer.process_data(data)

    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
