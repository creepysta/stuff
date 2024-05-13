from collections import defaultdict


class Entry:
    def __init__(self, value=None):
        self._entries = defaultdict(type(self))
        self.value = value

    def __getitem__(self, key):
        return self._entries[key]

    def __setitem__(self, key, val):
        self[key].value = val

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"Entry({self.value})"

e = Entry()
e["foo"]["bar"]["int"] = "1"
e["foo"]["bar"]["str"] = "foo"
e["foo"]["bar"]["baz"]["int"] = "1"
e["foo"]["bar"]["int"]["int"] = "99"
e["foo"]["bar"]["int"]["int"] = "100"

print(e["foo"]["bar"]["int"].value         , f'{e["foo"]["bar"]["int"]=}')
print(e["foo"]["bar"]["str"].value         , f'{e["foo"]["bar"]["str"]=}')
print(e["foo"]["bar"]["baz"]["int"].value  , f'{e["foo"]["bar"]["baz"]["int"]=}')
print(e["foo"]["bar"]["int"]["int"].value  , f'{e["foo"]["bar"]["int"]["int"]=}')
print(e["foo"]["bar"]["baz"]["nokey"].value, f'{e["foo"]["bar"]["baz"]["nokey"]=}')

