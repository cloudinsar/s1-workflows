from testutils import *


def test_parse_date():
    parse_date("2025-11-26")
    parse_date("20251126")
    parse_date("2025-1-26")
    parse_date("2025-01-1")
    parse_date("2024-08-09T00:00:00Z") # from the datetime picker in the openEO editor


def test_logging():
    setup_insar_environment()
    # print("Test print statement.")
    logging.info("This is an info message.")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.")
    # print("print should log as info")
    # print("Print should not crash on extra arguments", 123, {"key": "value"})
    # print("print should not crash with file redirect", file=sys.stderr)  # not sure if this is enough
