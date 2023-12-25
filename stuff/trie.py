class TList(list):
    def __getitem__(self, idx):
        if isinstance(idx, str):
            assert len(idx) == 1
            return super().__getitem__(ord(idx) - ord('a'))

        assert isinstance(idx, int)
        return super().__getitem__(idx)

    def __setitem__(self, idx, val):
        if isinstance(idx, str):
            assert len(idx) == 1
            return super().__setitem__(ord(idx) - ord('a'), val)

        assert isinstance(idx, int)
        return super().__setitem__(idx, val)


class Trie:
    ends: int
    children: TList

    def __init__(self):
        self.ends = 0
        self.children = TList([None for _ in range(26)])

    def __repr__(self):
        chars = [
            chr(i + ord('a'))
            for i, e in enumerate(self.children) if e
        ]
        return f"Trie(ends={self.ends}, children={chars})"

class Mgr:
    root: Trie
    def __init__(self):
        self.root = Trie()

    def insert(self, word: str):
        temp = self.root
        for c in word:
            if not temp.children[c]:
                temp.children[c] = Trie()

            temp = temp.children[c]


        temp.ends += 1

    def _search(self, node: Trie, curr = ""):
        if node.ends:
            yield curr

        for i, _ in enumerate(node.children):
            temp = node.children[i]
            if not temp: continue
            yield from self._search(temp, curr + chr(ord('a') + i))

    def search(self, word: str):
        temp = self.root
        curr = ""
        for c in word:
            if not temp.children[c]:
                return None

            curr += c
            temp = temp.children[c]

        return self._search(temp, curr)

"""
words = ["hello", "heyy", "there", "delilah", "how", "are", "you", "gonna", "delete", "your", "armchair", "yourself"]
m = Mgr()
for word in words:
    m.insert(word)

for pref in ["h", "he", "hel", "hey", "de", "del", "ar", "a", "y", "your", "yours"]:
    got = m.search(pref)
    print("PREFIX:", pref)
    if not got:
        continue

    for w in got:
        print(w)
"""
