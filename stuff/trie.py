from typing import List


class Trie:
    ends: int
    children: List

    def __init__(self):
        self.ends = 0
        self.children = [None for _ in range(26)]

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
            ch = ord(c) - ord('a')
            if not temp.children[ch]:
                temp.children[ch] = Trie()

            temp = temp.children[ch]


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
            ch = ord(c) - ord('a')
            if not temp.children[ch]:
                return None

            curr += c
            temp = temp.children[ch]

        return self._search(temp, curr)

"""
words = ["hello", "heyy", "there", "delilah", "how", "are", "you"]
m = Mgr()
for word in words:
    m.insert(word)

for pref in ["h", "he", "hel", "hey", "de", "del", "ar", "a", "y"]:
    got = m.search(pref)
    print("PREFIX:", pref)
    if not got:
        continue

    for w in got:
        print(w)

return 0
"""

