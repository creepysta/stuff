import pytest

from literedis import (
    BulkString,
    CommandType,
    Error,
    Redis,
    Trie,
    handle_command,
    parse_crlf,
    parse_data,
    serialize_data,
)

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


@pytest.fixture
def store():
    return Redis()


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
    expected = "*5\r\n:1\r\n:2\r\n*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n$-1\r\n:-3\r\n"
    assert got == expected


def test_ser_maps():
    data = {BulkString(5, "first"): 1, BulkString(6, "second"): "asd", 3: "third"}
    got = serialize_data(data)
    expected = "%3\r\n$5\r\nfirst\r\n:1\r\n$6\r\nsecond\r\n+asd\r\n:3\r\n+third\r\n"
    assert got == expected


def test_ser_sets():
    data = {1, 2, 3}
    got = serialize_data(data)
    parsed = parse_data(parse_crlf(got))
    assert parsed == data


def test_ping(store: Redis):
    cmd_type, res = handle_command("PING", [], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Ping
    assert rv == "PONG"


def test_echo(store: Redis):
    cmd_type, res = handle_command("ECHO", [BulkString(3, "Foo")], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Echo
    assert rv == "Foo"


def test_exists(store: Redis):
    store.set("Foo", 2)
    cmd_type, res = handle_command(
        "EXISTS",
        [BulkString(3, "Foo"), BulkString(3, "Bar"), BulkString(3, "baz")],
        store,
    )
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Exists
    assert rv == 1


def test_set(store: Redis):
    cmd_type, res = handle_command("SET", [BulkString(3, "Foo"), 1], store)
    rv = parse_data(parse_crlf(res))
    assert store.get("Foo") == "1"
    assert cmd_type == CommandType.Set
    assert rv == "OK"


def test_get(store: Redis):
    store.set("Foo", 999)
    cmd_type, res = handle_command("GET", [BulkString(3, "Foo")], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Get
    assert rv == "999"


def test_incr_no_prev(store: Redis):
    cmd_type, res = handle_command("INCR", [BulkString(3, "Foo")], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Incr
    assert rv == 1


def test_incr_with_prev(store: Redis):
    store.set("Foo", 1)
    cmd_type, res = handle_command("INCR", [BulkString(3, "Foo")], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Incr
    assert rv == 2


def test_decr_no_prev(store: Redis):
    cmd_type, res = handle_command("DECR", [BulkString(3, "Foo")], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Decr
    assert rv == -1


def test_decr_with_prev(store: Redis):
    store.set("Foo", 999)
    cmd_type, res = handle_command("DECR", [BulkString(3, "Foo")], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Decr
    assert rv == 998


def test_lpush_no_prev(store: Redis):
    cmd_type, res = handle_command("LPUSH", [BulkString(3, "Foo"), 1, 2, 3], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Lpush
    assert rv == 3
    assert store._get("Foo") == [3, 2, 1]


def test_lpush_with_prev(store: Redis):
    store.set("Foo", [999])
    cmd_type, res = handle_command("LPUSH", [BulkString(3, "Foo"), 1, 2, 3], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Lpush
    assert rv == 4
    assert store._get("Foo") == [3, 2, 1, 999]


def test_rpush_no_prev(store: Redis):
    cmd_type, res = handle_command("rpush", [BulkString(3, "Foo"), 1, 2, 3], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Rpush
    assert rv == 3
    assert store._get("Foo") == [1, 2, 3]


def test_rpush_with_prev(store: Redis):
    store.set("Foo", [999])
    cmd_type, res = handle_command("rpush", [BulkString(3, "Foo"), 1, 2, 3], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Rpush
    assert rv == 4
    assert store._get("Foo") == [999, 1, 2, 3]


def test_llen(store: Redis):
    store.set("Foo", [999, 991])
    cmd_type, res = handle_command("LLEN", ["Foo"], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Llen
    assert rv == 2


@pytest.mark.parametrize("low,high", [(0, 0), (0, 1), (1, 3), (0, -1), (1, -1)])
def test_lrange(store: Redis, low, high):
    data = [1, 2, 3, 4, 5, 6]
    store.set("Foo", data)
    cmd_type, res = handle_command("LRANGE", ["Foo", low, high], store)
    rv = parse_data(parse_crlf(res))
    expected = data[low : high + 1] if high >= 0 else data[low:]
    assert cmd_type == CommandType.Lrange
    assert rv == expected


def test_save(store: Redis):
    cmd_type, res = handle_command("save", [], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Save
    assert rv == "OK"


def test_hset_no_prev(store: Redis):
    cmd_type, res = handle_command(
        "HSET",
        [
            "foo:bar:baz",
            "Foo",
            "Bar",
            "Bar",
            "Baz",
        ],
        store,
    )
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Hset
    assert rv == 2
    assert store._get("foo:bar:baz") == {"Foo": "Bar", "Bar": "Baz"}


def test_hset_with_prev(store: Redis):
    store.hset("foo:bar:baz", ["foo", "bar", "baz", "boo"])
    cmd_type, res = handle_command(
        "HSET", ["foo:bar:baz", "foo", "bar", "hello", "world"], store
    )
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Hset
    assert rv == 3
    assert store._get("foo:bar:baz") == {"foo": "bar", "hello": "world", "baz": "boo"}


def test_hget(store: Redis):
    store.hset("foo:bar:baz", ["foo", "bar", "baz", "boo"])
    cmd_type, res = handle_command("HGET", ["foo:bar:baz", "foo"], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Hget
    assert rv == "bar"


def test_hmget(store: Redis):
    store.hset("foo:bar:baz", ["foo", "bar", "baz", "boo", "hello", "world"])
    cmd_type, res = handle_command(
        "HMGET", ["foo:bar:baz", "foo", "bar", "hello", "world"], store
    )
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Hmget
    assert rv == ["bar", None, "world", None]


def test_sadd(store: Redis):
    store.sadd("foo:bar:baz", ["foo:1", "bar"])
    cmd_type, res = handle_command("SADD", ["foo:bar:baz", "foo:2", "bar"], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Sadd
    assert rv == 1, 'could only set "foo:2" since "bar" was already present'
    assert set(store.smembers("foo:bar:baz")) == {"foo:1", "foo:2", "bar"}


def test_srem(store: Redis):
    store.sadd("foo:bar:baz", ["foo:1", "bar"])
    cmd_type, res = handle_command("SREM", ["foo:bar:baz", "foo:2", "bar"], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Srem
    assert rv == 1, 'could only remove "bar" since "foo:2" was not in the set'


def test_sinter(store: Redis):
    store.sadd("foo:bar", ["foo:1", "bar"])
    store.sadd("bar:baz", ["foo:2", "bar"])
    cmd_type, res = handle_command("SINTER", ["foo:bar", "bar:baz"], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Sinter
    assert set(rv) == {
        "bar",
    }, '"bar" is only common'


def test_sismember(store: Redis):
    store.sadd("foo:bar", ["foo:1", "bar"])
    cmd_type, res = handle_command("SISMEMBER", ["foo:bar", "foo:1"], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Sismember
    assert rv == True, '"foo:1" is only common'
    cmd_type, res = handle_command("SISMEMBER", ["foo:bar", "foo:2"], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Sismember
    assert rv == False, '"foo:2" should not present'


def test_scard(store: Redis):
    store.sadd("foo:bar", ["foo:1", "bar"])
    cmd_type, res = handle_command("SCARD", ["foo:bar"], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Scard
    assert rv == 2, '"foo:1", "bar" are the elements'


def test_smembers(store: Redis):
    store.sadd("foo:bar", ["foo:1", "bar"])
    cmd_type, res = handle_command("SMEMBERS", ["foo:bar"], store)
    rv = parse_data(parse_crlf(res))
    assert cmd_type == CommandType.Smembers
    assert set(rv) == {"foo:1", "bar"}, '"foo:1", "bar" are the elements'


@pytest.mark.parametrize(
    "prefix,count",
    [
        ("h", 3),
        ("he", 2),
        ("hel", 1),
        ("hey", 1),
        ("de", 2),
        ("del", 2),
        ("ar", 2),
        ("a", 2),
        ("y", 3),
        ("your", 2),
        ("yours", 1),
    ],
)
def test_trie(prefix, count):
    words = [
        "hello",
        "heyy",
        "there",
        "delilah",
        "how",
        "are",
        "you",
        "gonna",
        "delete",
        "your",
        "armchair",
        "yourself",
    ]
    m = Trie()
    for word in words:
        m.insert(word)

    got = m.search(prefix)
    rv = list(got)
    assert count == len(rv)
