# Uncomment this to pass the first stage
from functools import cached_property, wraps
import logging
from os import PathLike
import socket
import io
import sys
import struct
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from argparse import ArgumentParser
from enum import Enum
from threading import Thread
from typing import Any, Generator

logger = logging.getLogger("literedis")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class TList(list):
    low = ord('-')
    high = ord('9')
    def __getitem__(self, idx):
        if isinstance(idx, str):
            assert len(idx) == 1
            return super().__getitem__(ord(idx) - self.low)

        assert isinstance(idx, int)
        return super().__getitem__(idx)

    def __setitem__(self, idx, val):
        if isinstance(idx, str):
            assert len(idx) == 1
            return super().__setitem__(ord(idx) - self.low, val)

        assert isinstance(idx, int)
        return super().__setitem__(idx, val)


class TrieNode:
    ends: int
    children: TList

    def __init__(self):
        self.ends = 0
        self.children = TList([None for _ in range(15)])
        self.data = {}

    def __repr__(self):
        chars = [chr(i + ord("a")) for i, e in enumerate(self.children) if e]
        return f"Trie(ends={self.ends}, children={chars})"


# TODO: convert to Radix Tree
# https://en.wikipedia.org/wiki/Radix_tree
class Trie:
    root: TrieNode
    empty = True
    error_0_0 = ValueError("The ID specified in XADD must be greater than 0-0")
    error_key_lt_last_key = ValueError("The ID specified in XADD is equal or smaller than the target stream top item")

    def __init__(self):
        self.root = TrieNode()
        self.last_key = (0, 1)

    def _gen_next_ms(self):
        curr = int(time.time() * 1000)
        ms, seq = self.last_key
        if curr == ms:
            return ms, seq + 1

        return curr, 0

    def _gen_next_seq(self, key: str):
        ms = int(key.split('-')[0])
        pms, pseq = self.last_key
        if ms < pms:
            raise self.error_key_lt_last_key

        if self.empty:
            return self.last_key

        if ms == pms:
            return ms, pseq + 1

        return ms, 0

    def _ser_parts(self, parts: tuple[int, int]):
        return "-".join(map(str, parts))

    def _gen_next_key(self, key: str):
        if key == "*":
            return self._gen_next_ms()

        _, seq = key.split("-")
        if seq == "*":
            return self._gen_next_seq(key)

        raise ValueError(f"Invalid {key=}")

    def _check_key(self, key: str):
        if key == "0-0":
            raise self.error_0_0

        if "*" in key:
            return self._gen_next_key(key)

        ms, seq = map(int, key.split("-"))
        exception = self.empty and (ms, seq) == (0, 1)
        pms, pseq = self.last_key
        if not exception and any([ms < pms, ms == pms and seq <= pseq]):
            raise self.error_key_lt_last_key

        return ms, seq

    def insert(self, key: str, data: dict | None = None):
        parts = self._check_key(key)

        key = self._ser_parts(parts)
        temp = self.root
        for c in key:
            if not temp.children[c]:
                temp.children[c] = TrieNode()

            temp = temp.children[c]

        temp.ends += 1
        if data:
            temp.data = data

        self.last_key = parts
        self.empty = False
        return key

    def _search(self, node: TrieNode, curr="") -> Generator[tuple[str, dict], None, None]:
        if node.ends:
            yield (curr, node.data)

        for i, _ in enumerate(node.children):
            temp = node.children[i]
            if not temp:
                continue
            yield from self._search(temp, curr + chr(ord("-") + i))

    def search(self, key: str):
        temp = self.root
        curr = ""
        for c in key:
            if not temp.children[c]:
                return None

            curr += c
            temp = temp.children[c]

        return self._search(temp, curr)

    def _all(self, node: TrieNode, key=""):
        if node.ends:
            yield key, node.data

        for i, node in enumerate(node.children):
            if not node: continue
            yield from self._all(node, key + chr(ord("-") + i));

    def all(self):
        return self._all(self.root)



class ErrorType(Enum):
    Command = "command"
    InvalidData = "invalid_data"
    WrongType = "wrong_type_operation"


class Base:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        super().__init__()

    @property
    def _margs(self):
        args = ",".join(
            [
                f"{k}={v!r}"
                for k, v in vars(self).items()  # self.kwargs.items()
                if not (k.startswith("_"))
            ]
        )
        return args

    def __repr__(self):
        cons = f"{type(self).__name__}({self._margs})"
        return cons

    def __eq__(self, o):
        if not isinstance(o, type(self)):
            raise NotImplementedError()

        ok = True
        for k, v in vars(self).items():
            if not hasattr(self, k):
                continue

            ok = ok and (getattr(o, k) == v)

        return ok

    def __hash__(self):
        args = self._margs
        return hash(args)


class Error(Base):
    def __init__(self, msg: str, **kwargs):
        self.msg = msg
        super().__init__(msg=msg, **kwargs)

    def ser(self):
        return f"-ERR {self.msg}\r\n"

    def __str__(self):
        return self.msg


class BulkError(Error):
    def __init__(self, sz: int, msg: str, **kwargs):
        self.sz = sz
        self.msg = msg
        super().__init__(msg=msg, **kwargs)

    def ser(self):
        return f"!{self.sz}\r\n-Err: {self.msg}\r\n"

    def __str__(self):
        return self.msg


class BulkString(str):
    def __new__(cls, sz: int, data: str):
        # ref - https://stackoverflow.com/questions/7255655/how-to-subclass-str-in-python
        cls.sz = sz
        return super().__new__(cls, data)

    def __init__(self, sz: int, data: str):
        self.sz = sz
        self.data = data

    def __str__(self):
        return self.data

    def ser(self):
        return f"${self.sz}\r\n{self.data}\r\n"

    def __repr__(self):
        return f"{type(self).__name__}(sz={self.sz},data={self.data})"


def skip(f, free):
    if free :
        f.read(free)


def to_datetime(usecs_since_epoch):
    seconds_since_epoch = usecs_since_epoch // 1000000
    seconds_since_epoch = min(seconds_since_epoch, 221925052800)
    useconds = usecs_since_epoch % 1000000
    dt = datetime.utcfromtimestamp(seconds_since_epoch)
    delta = timedelta(microseconds = useconds)
    return dt + delta


def read_char(f):
    return struct.unpack('b', f.read(1))[0]

def read_uchar(f):
    return struct.unpack('B', f.read(1))[0]

def read_short(f):
    return struct.unpack('h', f.read(2))[0]

def read_ushort(f):
    return struct.unpack('H', f.read(2))[0]

def read_int(f):
    return struct.unpack('i', f.read(4))[0]

def read_uint(f):
    return struct.unpack('I', f.read(4))[0]

def read_uint_be(f):
    return struct.unpack('>I', f.read(4))[0]

def read_24bit_signed_number(f):
    s = b'0' + f.read(3)
    num = struct.unpack('i', s)[0]
    return num >> 8

def read_long(f):
    return struct.unpack('q', f.read(8))[0]

def read_ulong(f):
    return struct.unpack('Q', f.read(8))[0]

def read_ms_time(f):
    return to_datetime(read_ulong(f) * 1000)

def read_ulong_be(f):
    return struct.unpack('>Q', f.read(8))[0]

def read_binary_double(f):
    return struct.unpack('d', f.read(8))[0]

def read_binary_float(f):
    return struct.unpack('f', f.read(4))[0]

def string_as_hexcode(string):
    for s in string:
        if isinstance(s, int):
            logger.debug(hex(s))
        else:
            logger.debug(hex(ord(s)))


class Redis:
    config = {}
    def __init__(self):
        # TODO: consider mutex
        self.store = {}
        self._ts = {}

    def handle_config(self, subcmd: str, *args):
        assert subcmd, f"Invalid sub command to CONFIG: {subcmd!r} with {args=}"
        match subcmd.upper():
            case "GET":
                key = args[0]
                val = self.config.get(args[0])
                return [key, val]
            case "RESETSTAT":
                raise NotImplementedError(f"{subcmd!r} not implemented")
            case "REWRITE":
                raise NotImplementedError(f"{subcmd!r} not implemented")
            case "SET":
                raise NotImplementedError(f"{subcmd!r} not implemented")
            case _:
                raise NotImplementedError(f"{subcmd!r} not implemented")

    def keys(self, item: str, *args):
        match item:
            case "*":
                keys = list(self.store.keys())
                rem = filter(lambda x: self.get(x) is not None, keys)
                return list(rem)
            case _:
                raise NotImplementedError("Not handling case: {item!r}")

    def entry_type(self, key: str):
        match self.store.get(key):
            case str():
                return "string"
            case list():
                return "list"
            case set():
                return "set"
            case dict():
                return "hash"
            case Trie():
                return "stream"
            case None:
                return "none"
            case x:
                raise NotImplementedError("[entry_type]", f"{x!r} not yet parsed")


    def set(self, key, val, *px) -> str:
        self.store[key] = val
        if px:
            assert len(px) == 2, f"Invalid {px=} passed to set"
            assert px[0].lower() == "px", f"Invalid command passed to `set` {px=}"
            _exp = px[-1]
            if _exp is None:
                return "OK"

            if isinstance(_exp, datetime):
                curr = datetime.now()
                # consider for tests where rdb will parse datetime
                if _exp > curr:
                    self._ts[key] = ((_exp - curr).total_seconds() * 1000, time.time_ns() // int(1e6))
                else:
                    logger.warning(f"Not setting {key=}, {val=} since its expiry {_exp} <= {curr=}")
                    del self.store[key]
            else:
                exp = int(_exp)
                self._ts[key] = (exp, time.time_ns() // int(1e6))
        return "OK"

    def _get(self, key: str):
        ts = self._ts.get(key)
        if ts:
            curr = time.time_ns() // int(1e6)
            exp, then = ts
            is_valid = curr - then <= exp
            # TODO: handle passive removal of keys
            if not is_valid:
                del self._ts[key]
                del self.store[key]
                return None

        return self.store.get(key)

    def get(self, key: str) -> BulkString | None:
        if self._get(key) is None:
            return None

        item = str(self._get(key))
        return BulkString(len(item), item)

    def exists(self, keys: list) -> int:
        return sum([key in self.store.keys() for key in keys])

    def del_keys(self, keys: list) -> int:
        rv = 0
        for key in keys:
            if key in self.store.keys():
                rv += 1
                del self.store[key]

        return rv

    def incr(self, key: str) -> int | None:
        if self._get(key) is None:
            self.set(key, "0")

        if not (self.get(key).isnumeric() or self.get(key)[1:].isnumeric()):  # type: ignore
            return None

        self.set(key, int(self.get(key) or 0) + 1)
        return self._get(key)  # type: ignore

    def decr(self, key: str) -> int | None:
        if self._get(key) is None:
            self.set(key, "0")

        if not (self.get(key).isnumeric() or self.get(key)[1:].isnumeric()):  # type: ignore
            return None

        self.set(key, int(self.get(key) or 0) - 1)
        return self._get(key)  # type: ignore

    # https://web.archive.org/web/20201108091210/http://effbot.org/pyfaq/what-kinds-of-global-value-mutation-are-thread-safe.htm
    def lpush(self, key: str, vals: list) -> int | None:
        item = self._get(key)  # type: ignore
        if item is None:
            self.set(key, [])

        if not isinstance(self._get(key), list):
            return None

        item: list = self._get(key)  # type: ignore
        item[0:0] = vals[::-1]
        return len(self._get(key))  # type: ignore

    def rpush(self, key: str, vals: list) -> int | None:
        item = self._get(key)  # type: ignore
        if item is None:
            self.set(key, [])

        if not isinstance(self._get(key), list):
            return None

        item: list = self._get(key)  # type: ignore
        item.extend(vals)
        return len(self._get(key))  # type: ignore

    def llen(self, key: str) -> int | None:
        if self._get(key) is None:
            self.set(key, [])

        if not isinstance(self._get(key), list):
            return None

        return len(self._get(key))  # type: ignore

    def lrange(self, key: str, low: int, high: int) -> list | None:
        if self._get(key) is None:
            self.set(key, [])

        if not isinstance(self._get(key), list):
            return None

        if high == -1:
            return self._get(key)[low:]  # type: ignore

        return self._get(key)[low : high + 1]  # type: ignore

    def hset(self, key: str, vals: list) -> int | None:
        if self._get(key) is None:
            self.set(key, {})

        if not isinstance(self._get(key), dict):
            return None

        m: dict = self._get(key)  # type: ignore
        for name, val in zip(vals[::2], vals[1::2]):
            m[name] = val

        return len(m)

    def hget(self, key: str, mkey: str):
        stored = self._get(key) or {}
        return stored.get(mkey)

    def hmget(self, key: str, mkeys: list):
        stored = self._get(key) or {}
        rv = [stored.get(k) for k in mkeys]
        return rv

    def hgetall(self, key: str) -> list:
        stored = self._get(key) or {}
        rv = []
        for k, v in stored.items():
            rv.append(k)
            rv.append(v)

        return rv

    def hincrby(self, key: str, mkey: str, by: int) -> int:
        stored = self._get(key) or {}
        stored[mkey] = stored.get(mkey, 0) + by

        return stored[mkey]

    def sadd(self, key: str, vals: list) -> int | None:
        if self._get(key) is None:
            self.set(key, set())

        if not isinstance(self._get(key), set):
            return None

        s: set = self._get(key)  # type: ignore
        n = 0
        for val in vals:
            n += int(val not in s)
            s.add(val)

        return n

    def srem(self, key: str, vals: list) -> int | None:
        if self._get(key) is None:
            self.set(key, set())

        if not isinstance(self._get(key), set):
            return None

        s: set = self._get(key)  # type: ignore
        logger.debug(f"Set: {s!r}")
        n = 0
        for val in vals:
            if val not in s:
                continue

            n += 1
            s.remove(val)

        return n

    def sismember(self, key: str, val: str) -> int | None:
        if self._get(key) is None:
            self.set(key, set())

        if not isinstance(self._get(key), set):
            return None

        s: set = self._get(key)  # type: ignore
        return int(val in s)

    def sinter(self, s1: str, sets: list[str]) -> list | None:
        if self._get(s1) is None:
            self.set(s1, set())

        if not isinstance(self._get(s1), set):
            return None

        set1: set = self._get(s1)  # type: ignore
        rv = set1
        for s in sets:
            item = self._get(s)
            if item is None:
                self.set(s, set())
            if not isinstance(item, set):
                return None

            st: set = self._get(s)  # type: ignore
            rv = rv.intersection(st)

        return list(rv)

    def scard(self, key: str) -> int | None:
        if self._get(key) is None:
            self.set(key, set())

        if not isinstance(self._get(key), set):
            return None

        s: set = self._get(key)  # type: ignore
        return len(s)

    def smembers(self, key: str) -> list | None:
        if self._get(key) is None:
            self.set(key, set())

        if not isinstance(self._get(key), set):
            return None

        s: set = self._get(key)  # type: ignore
        return list(s)

    def xadd(self, key: str, node_key: str, *data):
        assert data, f"Got invalid {data=} to be stored for {key=} and ts={node_key!r}"
        if key not in self.store:
            self.store[key] = Trie()

        trie_: Trie = self.store[key]
        data_ = {k: v for k, v in zip(data[::2], data[1::2])}
        node_key = trie_.insert(node_key, data_)
        return node_key


    def dict_to_list(self, data: dict):
        rv = []
        for k, v in data.items():
            rv.extend([k, v])

        return rv

    def xrange(self, key: str, start: str, end: str, start_xlsv = False):
        trie: Trie = self.store.get(key)  # type: ignore
        if not trie:
            raise ValueError(f"{key=} is not set currently")

        items = trie.all()
        has_start = start != "-"
        has_end = end != "+"
        min_seq, max_seq = 0, (1<<64) - 1
        if has_start and "-" not in start:
            start += f"-{min_seq}"

        if has_end and "-" not in end:
            end += f"-{max_seq}"

        if has_start:
            start_i = tuple(map(int, start.split("-")))

        if has_end:
            end_i = tuple(map(int, end.split("-")))

        rv = []
        for key, data in items:
            ms, seq = map(int, key.split("-"))
            condition = True
            if has_end:
                condition = condition and (ms, seq) <= end_i
            if has_start:
                if start_xlsv:
                    condition = condition and start_i < (ms, seq)
                else:
                    condition = condition and start_i <= (ms, seq)

            if condition:
                rv.append([key, self.dict_to_list(data)])

        return rv

    def xread(self, count: int | None, block: int | None, *streams):
        n = len(streams)
        assert n % 2 == 0, "There should be even number of streams and corresponding Ids"
        rv = []
        pairs = [(name, start) for name, start in zip(streams[:n//2], streams[n//2:])]
        if block is not None:
            # TODO: handle 0 where the wait should be inf
            time.sleep(block//int(1e3))

        for name, start in pairs:
            got = self.xrange(name, start, "+", start_xlsv=True)
            if got:
                rv.append([name, got])

        return rv or BulkString(3, "nil")

    @classmethod
    def _aof_file(cls):
        return Path(cls.config.get('aof', 'redis.aof'))

    @classmethod
    def _rdb_file(cls) -> PathLike:
        fname = cls.config.get("dbfilename", "redis.rdb")
        direc = cls.config.get("dir", "/tmp/redis-files")
        return Path(direc) / fname

    @contextmanager
    def _aof(self):
        aof = self._aof_file()
        if not aof.exists():
            aof.write_text("")

        with aof.open("a") as f:
            yield f

    def save(self, query: str) -> str:
        if "GET" in query:
            logger.info(f"Skipping to persist READ {query=}")
            return "OK"

        q = query.replace("\r\n", "\\r\\n")

        with self._aof() as f:
            f.write(q + "\n")
        return "OK"


class rdb_consts:
    OPCODE_EOF = 0xFF
    OPCODE_SELECTDB = 0xFE
    OPCODE_EXPIRETIME = 0xFD
    OPCODE_EXPIRETIME_MS = 0xFC
    OPCODE_RESIZEDB = 0xFB
    OPCODE_AUX = 0xFA
    # OPCODE_MODULE_AUX = 247
    # OPCODE_IDLE = 0xF8
    # OPCODE_FREQ = 0xF9

    LEN_6BIT = 0b00
    LEN_14BIT = 0b01
    LEN_32BIT = 0b10
    ENCVAL = 0b11

    ENC_INT8 = 0
    ENC_INT16 = 1
    ENC_INT32 = 2
    ENC_LZF = 3

    TYPE_STRING = 0
    TYPE_LIST = 1
    TYPE_SET = 2
    TYPE_ZSET = 3
    TYPE_HASH = 4
    TYPE_HASH_ZIPMAP = 9
    TYPE_LIST_ZIPLIST = 10
    TYPE_SET_INTSET = 11
    TYPE_ZSET_ZIPLIST = 12
    TYPE_HASH_ZIPLIST = 13
    TYPE_LIST_QUICKLIST = 14
    TYPE_STREAM_LISTPACKS = 15

    DATA_TYPE_MAPPING = {0 : "string", 1 : "list", 2 : "set", 3 : "sortedset", 4 : "hash", 9 : "hash", 10 : "list", 11 : "set", 12 : "sortedset", 13 : "hash", 14 : "list", 15 : "stream"}


class RdbParser:
    """
----------------------------#
52 45 44 49 53              # Magic String "REDIS"
30 30 30 33                 # RDB Version Number as ASCII string. "0003" = 3
----------------------------
FA                          # Auxiliary field
$string-encoded-key         # May contain arbitrary metadata
$string-encoded-value       # such as Redis version, creation time, used memory, ...
----------------------------
FE 00                       # Indicates database selector. db number = 00
FB                          # Indicates a resizedb field
$length-encoded-int         # Size of the corresponding hash table
$length-encoded-int         # Size of the corresponding expire hash table
----------------------------# Key-Value pair starts
FD $unsigned-int            # "expiry time in seconds", followed by 4 byte unsigned int
$value-type                 # 1 byte flag indicating the type of value
$string-encoded-key         # The key, encoded as a redis string
$encoded-value              # The value, encoding depends on $value-type
----------------------------
FC $unsigned long           # "expiry time in ms", followed by 8 byte unsigned long
$value-type                 # 1 byte flag indicating the type of value
$string-encoded-key         # The key, encoded as a redis string
$encoded-value              # The value, encoding depends on $value-type
----------------------------
$value-type                 # key-value pair without expiry
$string-encoded-key
$encoded-value
----------------------------
FE $length-encoding         # Previous db ends, next db starts.
----------------------------
...                         # Additional key-value pairs, databases, ...

FF                          ## End of RDB file indicator
8-byte-checksum             ## CRC64 checksum of the entire file.
    """
    def __init__(self, path: str | PathLike, store: Redis | None = None) -> None:
        self._f = Path(path)
        self._store = store or Redis()
        self.aux_data = {}

    def parse(self):
        if not self._f.exists():
            return self._store

        with self._f.open('rb') as f:
            logger.debug(f"file content: {f.read()}")

        with self._f.open('rb') as f:
            self._verify_magic_string(f)
            self._verify_version(f)
            return self._parse(f)

    def _parse(self, f: io.BufferedReader) -> Redis:
        aux_byte = read_uchar(f)  # holds the opcode else the value_type
        match aux_byte:
            case rdb_consts.OPCODE_EOF:
                if self.rdb_version >= 5:
                    checksum = f.read(8)
                    logger.debug(f"{checksum=}")
                return self._store
            case rdb_consts.OPCODE_SELECTDB:
                logger.debug("parsing db selector")
                db_number = self._parse_db_selector(f)
                logger.debug(f"{db_number=}")
                return self._parse(f)
            case rdb_consts.OPCODE_EXPIRETIME:
                logger.debug("parsing expiry time")
                expiry = to_datetime(read_uint(f) * 1000000)
                logger.debug(f"SECONDS: {expiry=}")
                value_type = read_uchar(f)
                self._parse_key_value(f, value_type, expiry)
                return self._parse(f)
            case rdb_consts.OPCODE_EXPIRETIME_MS:
                logger.debug("parsing expiry time in millis")
                expiry = read_ms_time(f)
                logger.debug(f"MILLI SECS: {expiry=}")
                value_type = read_uchar(f)
                self._parse_key_value(f, value_type, expiry)
                return self._parse(f)
            case rdb_consts.OPCODE_RESIZEDB:
                logger.debug("parsing resizedb")
                db_size, expiry_db_size = self._parse_resizedb(f)
                logger.debug(f"{db_size=}, {expiry_db_size=}")
                return self._parse(f)
            case rdb_consts.OPCODE_AUX:
                logger.debug("parsing auxiliary fields")
                aux_kv = self._parse_aux(f)
                self.aux_data.update(aux_kv)
                logger.debug(f"{self.aux_data=}")
                return self._parse(f)
            case _:
                # key value pairs
                logger.debug("Parsing key value pairs")
                self._parse_key_value(f, aux_byte)
                return self._parse(f)

    def _verify_magic_string(self, f: io.BufferedReader):
        logger.debug(f"Parsing magic string")
        magic_string = f.read(5)
        logger.debug(f"{magic_string=}")
        if magic_string != b'REDIS':
            raise Exception('verify_magic_string', 'Invalid File Format')

    def _verify_version(self, f: io.BufferedReader):
        logger.debug(f"Parsing version")
        version_str = f.read(4)
        version = int(version_str)
        logger.debug(f"{version_str=} | {version=}")
        if version < 1 or version > 9:
            raise Exception('verify_version', 'Invalid RDB version number %d' % version)
        self.rdb_version = version

    def _parse_db_selector(self, f: io.BufferedReader):
        # skip the opcode
        length, _ = self._parse_length(f)
        return length

    def _parse_resizedb(self, f: io.BufferedReader) -> tuple[int, int]:
        db_size, _ = self._parse_length(f)
        expiry_db_size, _ = self._parse_length(f)
        return db_size, expiry_db_size

    def _parse_aux(self, f: io.BufferedReader) -> dict:
        key = self._parse_str(f)
        logger.debug(f"Aux string {key=}")
        value = self._parse_str(f)
        logger.debug(f"Aux string {value=}")
        return {key: value}

    def _parse_key_value(self, f: io.BufferedReader, value_type, expiry: datetime | None = None):
        # TODO: parse expired values
        logger.debug(f"{value_type=}")
        key = self._parse_str(f)
        logger.debug(f"{key=}")

        match value_type:
            case rdb_consts.TYPE_STRING:
                value = self._parse_str(f)
                logger.debug(f"PARSING TYPE STRING: {key=} {value=} {expiry=}")
                self._store.set(key, value, "px", expiry)
            case x:
                raise NotImplementedError("[_parse_key_value]", f"not implemented yet! {x!r}")

    def _parse_str(self, f: io.BufferedReader):
        length, is_encoded = self._parse_length(f)
        logger.debug(f"Parsing string: {length=} | {is_encoded=}")
        if not is_encoded:
            content = f.read(length)
            logger.debug(f"Got string {content=}")
            return content.decode('utf-8')

        match length:
            case rdb_consts.ENC_INT8:
                return read_char(f)
            case rdb_consts.ENC_INT16:
                return read_short(f)
            case rdb_consts.ENC_INT32:
                return read_int(f)
            case rdb_consts.ENC_LZF:
                # The compressed length clen is read from the stream using Length Encoding
                # The uncompressed length is read from the stream using Length Encoding
                # The next clen bytes are read from the stream
                # Finally, these bytes are decompressed using LZF algorithm
                clen, _ = self._parse_length(f)
                uncomp_len, _ = self._parse_length(f)
                bytes_ = f.read(clen)
                # val = lzf.decompress(f.read(clen), uncomp_len)
                raise NotImplementedError(
                    "_parse_str",
                    f"compressed string: {rdb_consts.ENC_LZF!r} {clen=}, {uncomp_len=}, {bytes_=}"
                )
            case x:
                raise NotImplementedError(
                    "_parse_str",
                    f"Unknown string type: {x!r}"
                )

    def _parse_length(self, f: io.BufferedReader) -> tuple[int, bool]:
        first_byte = read_uchar(f)
        msb = first_byte >> 6
        logger.debug(f"Parsing length: {first_byte=} {msb=}")
        lsb6 = 0b00111111
        match msb:
            case rdb_consts.LEN_6BIT:
                # next six bits represent the length
                length = first_byte & lsb6
                return length, False
            case rdb_consts.LEN_14BIT:
                # read one additional byte. the combined 14 bits represents the length
                next_byte = read_uchar(f)
                length = ((first_byte & lsb6) << 8) | next_byte
                return length, False
            case rdb_consts.LEN_32BIT:
                # discard the remaining 6 bits. the next 4 bytes represents the length
                length = read_uint_be(f)
                return length, False
            case rdb_consts.ENCVAL:
                # the next object is encoded in a special format
                # the remaining 6 bits indicate the format
                return (first_byte & lsb6), True
            case x:
                raise NotImplementedError(f"[_parse_length] Unknown msb: {x!r}")



class CommandType(Enum):
    NoOp = "NOOP"
    Ping = "PING"
    Del = "DEL"
    Echo = "ECHO"
    Exists = "EXISTS"
    Get = "GET"
    Set = "SET"
    Incr = "INCR"
    Decr = "DECR"
    Save = "SAVE"
    Lpush = "LPUSH"
    Lpop = "LPOP"
    Rpush = "RPUSH"
    Rpop = "RPOP"
    Llen = "LLEN"
    Lrange = "LRANGE"
    Hset = "HSET"
    Hget = "HGET"
    Hmget = "HMGET"
    Hgetall = "HGETALL"
    Hincrby = "HINCRBY"
    Sadd = "SADD"
    Srem = "Srem"
    Sismember = "SISMEMBER"
    Sinter = "SINTER"
    Scard = "SCARD"
    Smembers = "SMEMBERS"
    Client = "CLIENT"
    Config = "CONFIG"
    Keys = "KEYS"
    Type = "TYPE"
    Xadd = "XADD"
    Xrange = "XRANGE"
    Xread = "XREAD"

    Error = "Error"  # required for internal use

    def __eq__(self, o):
        if isinstance(o, str):
            return self.value.lower() == o.lower()

        return super().__eq__(o)


def handle_err(cmd: str | None, args: list[str] | None, error_type: ErrorType) -> str:
    match error_type:
        case ErrorType.Command:
            return f"-ERR unknown command {cmd!r}\r\n"
        case ErrorType.WrongType:
            return (
                "-WRONGTYPE Operation against a key holding the wrong kind"
                f"of value {args=}"
            )
        case ErrorType.InvalidData:
            return f"-ERR invalid input, cannot parse data: {cmd!r}"


def command_echo(data: list[str]) -> tuple[CommandType, str]:
    rdata = " ".join(data)
    resp = f"+{rdata}\r\n"
    return CommandType.Echo, resp


def command_ping() -> tuple[CommandType, str]:
    return CommandType.Ping, "+PONG\r\n"


def parse_crlf(data: str) -> Generator[str, None, None]:
    token = ""
    for ch in data:
        if ch in ("\r"):
            yield token
            token = ""
            continue
        elif ch == "\n":
            continue

        token += ch


def _next(gen: Generator) -> str | None:
    try:
        return next(gen)
    except StopIteration:
        return None


def next_token(data: Generator) -> str | None:
    return _next(data)


def parse_nulls() -> None:
    return None


def parse_int(token):
    match (token[0], token[1:]):
        case ("+", rest):
            return int(rest)
        case ("-", rest):
            return -int(rest)
        case _:
            return int(token)


def parse_bool(token):
    match token:
        case "t":
            return True
        case "f":
            return False
        case x:
            raise ValueError(f"Given input is not boolean : {x=}")


def parse_bulk_strings(sz, tokens) -> BulkString | None:
    if sz == -1:
        return None
    token = next(tokens)
    assert len(token) == sz
    return BulkString(len(token), token)


def parse_bulk_errors(sz, tokens) -> BulkError:
    token = next(tokens)
    assert len(token) == sz
    return BulkError(sz, token)


def parse_array(sz, tokens) -> list | None:
    if sz == -1:
        return None

    rv = []
    for _ in range(sz):
        parsed_token = parse_data(tokens)
        rv.append(parsed_token)

    return rv


def parse_sets(sz, tokens) -> set:
    rv = set()
    for _ in range(sz):
        parsed_token = parse_data(tokens)
        rv.add(parsed_token)

    return rv


def parse_maps(sz, tokens) -> dict:
    rv = {}
    for _ in range(sz):
        key = parse_data(tokens)
        val = parse_data(tokens)
        rv[key] = val

    return rv


def parse_simple_strings(token):
    return token


def parse_errors(token):
    return Error(token)


def parse_data(tokens):
    token = next_token(tokens)
    if token is None:
        return

    match (token[0], token[1:]):
        case ("+", rest):
            return parse_simple_strings(rest)
        case ("-", rest):
            return parse_errors(rest)
        case (":", rest):
            return parse_int(rest)
        case ("_", _):
            return parse_nulls()
        case ("#", rest):
            return parse_bool(rest)
        case ("!", rest):
            return parse_bulk_errors(int(rest), tokens)  # Simple
        case ("$", rest):
            return parse_bulk_strings(int(rest), tokens)
        case ("*", rest):
            return parse_array(int(rest), tokens)
        case ("%", rest):
            return parse_maps(int(rest), tokens)
        case ("~", rest):
            return parse_sets(int(rest), tokens)
        # case (",", _):
        #     # return doubles()
        # case ("(", _):
        #     # return big_numbers()
        # case ("=", _):
        #     # return verbatim_strings()
        # case (">", _):
        #     # return pushes()   # Agg
        case _:
            return None


def serialize_int(val: int) -> str:
    return ":{val}\r\n".format(val=str(val))


def serialize_str(val: str) -> str:
    return "+{val}\r\n".format(val=val)


def serialize_bulk_str(val: BulkString) -> str:
    return val.ser()


def serialize_bool(val: bool) -> str:
    return "#{val}\r\n".format(val="t" if val is True else "f")


def serialize_null() -> str:
    return "$-1\r\n"
    return "*-1\r\n"
    return "_\r\n"


def serialize_dict(data: dict) -> str:
    rv = f"%{len(data)}\r\n"
    for key, val in data.items():
        rv += serialize_data(key)
        rv += serialize_data(val)

    return rv


def serialize_list(data: list) -> str:
    rv = f"*{len(data)}\r\n"
    for item in data:
        rv += serialize_data(item)

    return rv


def serialize_set(data: set) -> str:
    rv = f"~{len(data)}\r\n"
    for item in data:
        rv += serialize_data(item)

    return rv


def serialize_error(data: Error) -> str:
    return data.ser()


def serialize_bulk_error(data: BulkError) -> str:
    return data.ser()


def serialize_data(data) -> str:
    match data:
        case int():
            return serialize_int(data)
        case BulkString():
            return serialize_bulk_str(data)
        case str():
            return serialize_str(data)
        case bool():
            return serialize_bool(data)
        case None:
            return serialize_null()
        case dict():
            return serialize_dict(data)
        case list():
            return serialize_list(data)
        case set():
            return serialize_set(data)
        case BulkError():
            return serialize_bulk_error(data)  # Simple
        case Error():
            return serialize_error(data)
        # case float():
        #     return float():
        # case ("(", _):
        #     # return big_numbers()
        # case ("=", _):
        #     # return verbatim_strings()
        # case ("~", _):
        #     # return sets()
        # case (">", _):
        #    # return pushes()   # Agg
        case _:
            return serialize_null()


def handle_exceptions(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            rv = func(*args, **kwargs)
            return rv
        except Exception as e:
            return CommandType.Error, serialize_error(Error(str(e)))

    return inner


@handle_exceptions
def handle_command(command: str, body: list, store: Redis) -> tuple[CommandType | None, Any]:
    match command.upper():
        case CommandType.Ping:
            return CommandType.Ping, serialize_data("PONG")
        case CommandType.Echo:
            rv = serialize_data(body[0])
            return CommandType.Echo, rv
        case CommandType.Exists:
            resp = store.exists(body)
            rv = serialize_data(resp)
            return CommandType.Exists, rv
        case CommandType.Set:
            resp = store.set(body[0], body[1], *body[2:])
            rv = serialize_data(resp)
            return CommandType.Set, rv
        case CommandType.Get:
            rv = serialize_data(store.get(body[0]))
            return CommandType.Get, rv
        case CommandType.Incr:
            resp = store.incr(body[0])
            rv = serialize_data(resp)
            if resp is None:
                rv = serialize_data(
                    Error(
                        f"Cannot increment data for key={body[0]}."
                        f" Current value stored: {store.get(body[0])!r}"
                    )
                )
            return CommandType.Incr, rv
        case CommandType.Decr:
            resp = store.decr(body[0])
            rv = serialize_data(resp)
            if resp is None:
                rv = serialize_data(
                    Error(
                        f"Cannot decrement data for key={body[0]}."
                        f" Current value stored: {store.get(body[0])!r}"
                    )
                )
            return CommandType.Decr, rv
        case CommandType.Lpush:
            resp = store.lpush(body[0], body[1:])
            rv = serialize_data(resp)
            if resp is None:
                rv = serialize_data(
                    Error(
                        f"Cannot perform LPUSH for key={body[0]}."
                        f" Current value stored: {store.get(body[0])!r}"
                    )
                )
            return CommandType.Lpush, rv
        case CommandType.Rpush:
            resp = store.rpush(body[0], body[1:])
            rv = serialize_data(resp)
            if resp is None:
                rv = serialize_data(
                    Error(
                        f"Cannot perform RPUSH for key={body[0]}."
                        f" Current value stored: {store.get(body[0])!r}"
                    )
                )
            return CommandType.Rpush, rv
        case CommandType.Lpop:
            raise NotImplementedError()
        case CommandType.Rpop:
            raise NotImplementedError()
        case CommandType.Llen:
            resp = store.llen(body[0])
            rv = serialize_data(resp)
            return CommandType.Llen, rv
        case CommandType.Lrange:
            resp = store.lrange(body[0], int(body[1]), int(body[2]))
            rv = serialize_data(resp)
            return CommandType.Lrange, rv
        case CommandType.Hset:
            resp = store.hset(body[0], body[1:])
            rv = serialize_data(resp)
            return CommandType.Hset, rv
        case CommandType.Hget:
            resp = store.hget(body[0], body[1])
            rv = serialize_data(resp)
            return CommandType.Hget, rv
        case CommandType.Hmget:
            resp = store.hmget(body[0], body[1:])
            rv = serialize_data(resp)
            return CommandType.Hmget, rv
        case CommandType.Hgetall:
            resp = store.hgetall(body[0])
            rv = serialize_data(resp)
            return CommandType.Hgetall, rv
        case CommandType.Hincrby:
            raise NotImplementedError("Not yet implemented: HINCRBY")
        case CommandType.Sadd:
            resp = store.sadd(body[0], body[1:])
            rv = serialize_data(resp)
            return CommandType.Sadd, rv
        case CommandType.Srem:
            resp = store.srem(body[0], body[1:])
            rv = serialize_data(resp)
            return CommandType.Srem, rv
        case CommandType.Sismember:
            resp = store.sismember(body[0], body[1])
            rv = serialize_data(resp)
            return CommandType.Sismember, rv
        case CommandType.Sinter:
            resp = store.sinter(body[0], body[1:])
            rv = serialize_data(resp)
            return CommandType.Sinter, rv
        case CommandType.Scard:
            resp = store.scard(body[0])
            rv = serialize_data(resp)
            return CommandType.Scard, rv
        case CommandType.Smembers:
            resp = store.smembers(body[0])
            rv = serialize_data(resp)
            return CommandType.Smembers, rv
        case CommandType.Client:
            return CommandType.Client, serialize_data("Ok")
        case CommandType.Config:
            resp = store.handle_config(body[0], *body[1:])
            return CommandType.Config, serialize_data(resp)
        case CommandType.Keys:
            resp = store.keys(body[0], *body[1:])
            return CommandType.Keys, serialize_data(resp)
        case CommandType.Type:
            resp = store.entry_type(body[0])
            return CommandType.Type, serialize_str(resp)
        case CommandType.Xadd:
            resp = store.xadd(body[0], body[1], *body[2:])
            return CommandType.Xadd, serialize_data(resp)
        case CommandType.Xrange:
            resp = store.xrange(body[0], body[1], body[2])
            return CommandType.Xrange, serialize_data(resp)
        case CommandType.Xread:
            block, count = None, None
            lowered = [x.lower() for x in body]
            stream_start = lowered.index("streams") + 1
            if "block" in lowered:
                block = int(lowered[lowered.index("block") + 1])

            if "count" in lowered:
                block = int(lowered[lowered.index("count") + 1])

            logger.debug(f"{block=} | {count=} | {stream_start=} | {lowered=}")
            resp = store.xread(count, block, *body[stream_start:])
            return CommandType.Xread, serialize_data(resp)
        case _:
            return None, serialize_error(Error("Invalid command: {command=} | {body=}"))


def parse_aof(store: Redis):
    aof = Redis._aof_file()
    if not aof.exists():
        return

    rv = []
    hist = aof.read_text()
    for query in hist.split('\n'):
        if not query: continue
        data = query.replace('\\r\\n', '\r\n')
        tokens = parse_crlf(data)
        res: list = parse_data(tokens)  # type: ignore
        try:
            got = handle_command(res[0], res[1:], store)
            rv.append(got)
        except Exception as e:
            logger.warning(f"Failed to recover {query=} with error: {e=}")

    return rv


def recover(store: Redis):
    parse_aof(store)
    RdbParser(store._rdb_file(), store).parse()



def get_response(data, store: Redis):
    tokens = parse_crlf(data)
    res = parse_data(tokens)
    logger.debug(f"{res=}")
    match res:
        case list() if len(res) > 0:
            store.save(data)
            rv = handle_command(res[0], res[1:], store)
            return rv
        case _:
            return (
                None,
                Error(
                    f"Invalid data recieved from client. Expected list, got {data=}"
                ).ser(),
            )


def read_data(client: socket.socket) -> str:
    data = ""
    client.settimeout(60.0)
    while r := client.recv(1024):
        data += r.decode("utf-8")
        if len(r) < 1024 or not r:
            break

    return data


def handle_client(client: socket.socket, store: Redis):
    logger.info(f"Client connected: {client.getpeername()}")
    while data := read_data(client):
        logger.debug(f"Got data: {data=}")
        try:
            ctype, res = get_response(data, store)
            logger.debug(f"Response: {res=}")
            client.sendall(res.encode("utf-8"))
            if ctype is None:
                break
        except Exception as e:
            logger.exception(f"Invalid command: {data}. Failed with error: {e}")
            break

    client.close()


def serve(host: str, port: int, store: Redis):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    addr = (host, port)
    sock.bind(addr)
    sock.listen(5)
    while True:
        client, _ = sock.accept()
        # TODO: get rid of threads
        t = Thread(target=handle_client, args=(client, store))
        t.start()


def main(argv: list[str] | None = None):
    parser = ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--dir")
    parser.add_argument("--dbfilename")
    args = parser.parse_args(argv)

    store = Redis()
    if args.dir or args.dbfilename:
        Redis.config['dir'] = args.dir
        Redis.config['dbfilename'] = args.dbfilename

    if args.serve:
        host = "localhost"
        port = 6379
        logger.info(f"Server listening on {host=}, {port=}")
        recover(store)
        serve(host, port, store)


if __name__ == "__main__":
    main()
