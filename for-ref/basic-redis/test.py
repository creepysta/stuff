import pytest

from main import Error, parse_crlf, parse_data, serialize_data

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
    ("-something went wrong\r\n", "-Err: something went wrong"),
]
bulk_string_data = [
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
        [[1, 2, 3], ["Hello", Error("World")]],
    ),
]
map_data = [("%2\r\n+first\r\n:1\r\n+second\r\n:2\r\n", {"first": 1, "second": 2})]
set_data = [
    ("~3\r\n$5\r\nhello\r\n$-1\r\n$5\r\nworld\r\n", {"hello", None, "world"}),
    ("~5\r\n:1\r\n:2\r\n:3\r\n:4\r\n$5\r\nhello\r\n", {1, 2, 3, 4, "hello"}),
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
    assert str(got) == expected


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
def test_sets(data, expected):
    gen = parse_crlf(data)
    got = parse_data(gen)
    assert len(got.intersection(expected)) == len(expected)
    assert len(got.intersection(expected)) == len(got)


def test_ser_array():
    data = [1, 2, ["hello", "world"], None, -3]
    got = serialize_data(data)
    expected = "*5\r\n:1\r\n:2\r\n*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n_\r\n:-3\r\n"
    assert got == expected


def test_ser_maps():
    data = {"first": 1, "second": "asd", 3: "third"}
    got = serialize_data(data)
    expected = (
        "%3\r\n$5\r\nfirst\r\n:1\r\n$6\r\nsecond\r\n$3\r\nasd\r\n:3\r\n$5\r\nthird\r\n"
    )
    assert got == expected


# TODO: think of ordering
def test_ser_sets():
    # data = {1, 2, 3}
    # got = serialize_data(data)
    # expected = "*5\r\n:1\r\n:2\r\n*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n_\r\n:-3\r\n"
    # assert got == expected
    pass
