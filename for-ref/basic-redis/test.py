import pytest
from main import parse_crlf, parse_data


int_data = [
    (":+123\r\n", 123),
    (":-123\r\n", -123),
    (":123\r\n", 123),
]
bool_data = [
    ("#t\r\n", True),
    ("#f\r\n", False),
]


@pytest.mark.parametrize("data,expected", int_data)
def test_int(data, expected):
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert got == expected


@pytest.mark.parametrize("data,expected", bool_data)
def test_bool(data, expected):
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert got is expected


def test_array():
    data = "*3\r\n:-1\r\n:2\r\n*1\r\n:+999\r\n"
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert got == [-1, 2, [999]]
