from testutils import *


def test_parse_date():
    parse_date("2025-11-26")
    parse_date("20251126")


def test_logging():
    logging.info("This is an info message.")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.")
    print("print should log as info")
    print("Print should not crash on extra arguments", 123, {"key": "value"})
    print("print should not crash with file redirect", file=sys.stderr)  # not sure if this is enough
