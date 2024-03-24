from collections.abc import MutableMapping
from contextlib import suppress
from operator import itemgetter
import sqlite3


class SQLDict(MutableMapping):
    """
    >>> d = SQLDict('kv-store')
    >>> d['foo'] = 'bar'
    >>> d['baz'] = 'hello'
    >>> print(d.items())
    >>> if 'foo' in d:
    >>>     print('foo in d')

    >>> del d['foo']
    >>> print(d.items())
    >>> if 'foo' not in d:
    >>>     print('foo not in d')
    """
    def __init__(self, dbname: str, items=(), **kw):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname)
        cur = self.conn.cursor()
        with suppress(sqlite3.OperationalError):
            cur.execute("CREATE TABLE IF NOT EXISTS Dict (key text, value text)");
            cur.execute("CREATE UNIQUE INDEX Kndx ON Dict (key)")

        self.update(**kw)


    def __setitem__(self, key, value):
        if key in self:
            del self[key]

        with self.conn as c:
            c.execute("INSERT INTO Dict VALUES (?, ?)", (key, value))

    def __getitem__(self, key):
        query = self.conn.execute("SELECT value from Dict where key = ?", (key,))

        item =  query.fetchone()
        if item is None:
            raise KeyError(f"{key=} doesn't exist in the dict")

        return item[0]

    def __delitem__(self, key) -> None:
        if key not in self:
            raise KeyError(f"{key=} doesn't exist in the dict")

        with self.conn as c:
            c.execute("DELETE FROM Dict where key = ?", (key, ))

    def __len__(self, key):
        return next(self.conn.execute("SELECT COUNT(*) from Dict"))[0]

    def __iter__(self):
        c = self.conn.execute("SELECT key FROM Dict")
        return map(itemgetter(0), c.fetchall())

    def close(self):
        self.conn.close()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(dbname={self.dbname!r}, items={list(self.items())})"
