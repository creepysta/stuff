import pytest

from main import BulkString, Error, parse_crlf, parse_data, serialize_data

int_data = [
    (":+123\r\n", 123),
    (":-123\r\n", -123),
    (":123\r\n", 123),
]
bool_data = [
    ("#t\r\n", True),
    ("#f\r\n", False),
]
string_data = [
    ("+Hello World\r\n", "Hello World"),
    ("+Ok\r\n", "Ok"),
]
err_data = [
    ("-something went wrong\r\n", Error("something went wrong")),
]
bulk_string_data = [
    ("$0\r\n\r\n", BulkString(0, "")),
    ("$-1\r\n", None),
    ("$5\r\nhello\r\n", BulkString(5, "hello")),
    ("$11\r\nhello world\r\n", BulkString(11, "hello world")),
]
array_data = [
    ("*0\r\n", []),
    ("*-1\r\n", None),
    ("*3\r\n:-1\r\n:2\r\n*1\r\n:+999\r\n", [-1, 2, [999]]),
    (
        "*3\r\n$5\r\nhello\r\n$-1\r\n$5\r\nworld\r\n",
        [BulkString(5, "hello"), None, BulkString(5, "world")],
    ),
    (
        "*5\r\n:1\r\n:2\r\n:3\r\n:4\r\n$5\r\nhello\r\n",
        [1, 2, 3, 4, BulkString(5, "hello")],
    ),
    (
        "*2\r\n*3\r\n:1\r\n:2\r\n:3\r\n*2\r\n+Hello\r\n-World\r\n",
        [[1, 2, 3], ["Hello", Error("World")]],
    ),
]
map_data = [
    (
        "%2\r\n+first\r\n:1\r\n+second\r\n:2\r\n",
        {"first": 1, "second": 2},
    ),
    (
        "%2\r\n$5\r\nfirst\r\n:1\r\n+second\r\n:2\r\n",
        {BulkString(5, "first"): 1, "second": 2},
    ),
]
set_data = [
    (
        "~3\r\n$5\r\nhello\r\n$-1\r\n$5\r\nworld\r\n",
        {BulkString(5, "hello"), None, BulkString(5, "world")},
    ),
    (
        "~5\r\n:1\r\n:2\r\n:3\r\n:4\r\n$5\r\nhello\r\n",
        {1, 2, 3, 4, BulkString(5, "hello")},
    ),
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


@pytest.mark.parametrize("data,expected", bulk_string_data)
def test_bulk_string(data, expected):
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert got == expected


@pytest.mark.parametrize("data,expected", string_data)
def test_simple_string(data, expected):
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert got == expected


@pytest.mark.parametrize("data,expected", err_data)
def test_parse_error(data, expected):
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert got == expected


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


@pytest.mark.parametrize("data,expected", set_data)
def test_sets(data, expected: set):
    gen = parse_crlf(data)
    got: set = parse_data(gen)  # type: ignore
    assert len(got.intersection(expected)) == len(expected)
    assert len(got.intersection(expected)) == len(got)


def test_ser_array():
    data = [1, 2, [BulkString(5, "hello"), BulkString(5, "world")], None, -3]
    got = serialize_data(data)
    expected = "*5\r\n:1\r\n:2\r\n*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n_\r\n:-3\r\n"
    assert got == expected


def test_ser_maps():
    data = {BulkString(5, "first"): 1, BulkString(6, "second"): "asd", 3: "third"}
    got = serialize_data(data)
    expected = (
        "%3\r\n$5\r\nfirst\r\n:1\r\n$6\r\nsecond\r\n+asd\r\n:3\r\n+third\r\n"
    )
    assert got == expected


# TODO: think of ordering
def test_ser_sets():
    # data = {1, 2, 3}
    # got = serialize_data(data)
    # expected = "*5\r\n:1\r\n:2\r\n*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n_\r\n:-3\r\n"
    # assert got == expected
    pass
