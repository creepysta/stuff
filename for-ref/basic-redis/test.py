import pytest

from main import Error, parse_crlf, parse_data

int_data = [
    (":+123\r\n", 123),
    (":-123\r\n", -123),
    (":123\r\n", 123),
]
bool_data = [
    ("#t\r\n", True),
    ("#f\r\n", False),
]
bulkstring_data = [
    ("$0\r\n\r\n", ""),
    ("$-1\r\n", None),
    ("$5\r\nhello\r\n", "hello"),
    ("$11\r\nhello world\r\n", "hello world"),
]
array_data = [
    ("*0\r\n", []),
    ("*-1\r\n", None),
    ("*3\r\n:-1\r\n:2\r\n*1\r\n:+999\r\n", [-1, 2, [999]]),
    ("*3\r\n$5\r\nhello\r\n$-1\r\n$5\r\nworld\r\n", ["hello", None, "world"]),
    ("*5\r\n:1\r\n:2\r\n:3\r\n:4\r\n$5\r\nhello\r\n", [1, 2, 3, 4, "hello"]),
    (
        "*2\r\n*3\r\n:1\r\n:2\r\n:3\r\n*2\r\n+Hello\r\n-World\r\n",
        [[1, 2, 3], ["Hello", str(Error("World"))]],
    ),
]
map_data = [
    ("%2\r\n+first\r\n:1\r\n+second\r\n:2\r\n", {"first": 1, "second": 2})
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


@pytest.mark.parametrize("data,expected", bulkstring_data)
def test_bulkstring(data, expected):
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert got == expected


def test_simple_string():
    gen = parse_crlf("+OK\r\n")
    got = parse_data(gen)
    assert got == "OK"


def test_parse_error():
    gen = parse_crlf("-something went wrong\r\n")
    got = parse_data(gen)
    assert str(got) == "-Err: something went wrong"


def test_nulls():
    gen = parse_crlf("_\r\n")
    got = parse_data(gen)
    assert got is None


@pytest.mark.parametrize("data,expected", array_data)
def test_array(data, expected):
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert got == expected


@pytest.mark.parametrize("data,expected", map_data)
def test_maps(data, expected):
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert got == expected
