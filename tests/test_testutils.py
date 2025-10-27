import datetime

from testutils import *


def test_parse_date():
    import datetime

    d = datetime.datetime(2021, 1, 10)
    assert d == parse_date("2021-01-10")
    assert d == parse_date("20210110")


def test_parse_date_tuple():
    t = parse_date_tuple("20240809_20240821")
    assert t == ("2024-08-09", "2024-08-21")
