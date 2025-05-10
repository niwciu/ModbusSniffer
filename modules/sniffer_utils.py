import serial

def normalize_sniffer_config(
    port,
    baudrate,
    parity_str,
    timeout_input,
    log_to_file=False,
    raw=False,
    raw_only=False,
    daily_file=False,
    csv=False,
    GUI = False,
):
    if parity_str == "none":
        parity = serial.PARITY_NONE
    elif parity_str == "even":
        parity = serial.PARITY_EVEN
    else:
        parity = serial.PARITY_ODD

    timeout = timeout_input

    if (raw or raw_only) and ( not GUI):
        log_to_file = True

    if csv:
        daily_file = True

    return {
        "port": port,
        "baudrate": baudrate,
        "parity": parity,
        "timeout": timeout,
        "raw_log": raw,
        "raw_only": raw_only,
        "csv_log": csv,
        "daily_file": daily_file,
        "log_to_file": log_to_file
    }
