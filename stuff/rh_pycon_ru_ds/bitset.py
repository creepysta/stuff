from collections.abc import MutableSet

class BitSet(MutableSet):
    """
    >>> b2 = BitSet(20, [1,11,3,13])
    >>> b1 = BitSet(20, [2, 4 ,3,13])
    >>> b2      # BitSet(limit=20, iterable=[1, 3, 11, 13])
    >>> b1      # BitSet(limit=20, iterable=[2, 3, 4, 13])
    >>> b2 & b1 # BitSet(limit=20, iterable=[3, 13])
    >>> b2 | b1 # BitSet(limit=20, iterable=[1, 2, 3, 4, 11, 13])
    >>> b2 - b1 # BitSet(limit=20, iterable=[1, 11])
    >>> b1 - b2 # BitSet(limit=20, iterable=[2, 4])
    >>> b1.add(15)
    """
    def __init__(self, limit: int, iterable=()):
        self.limit = limit
        num_bytes = (limit + 7) // 8
        self.data = bytearray(num_bytes)
        self |= iterable

    def __contains__(self, item):
        bytenum, bitnum = self._get_location(item)
        return bool((self.data[bytenum] >> bitnum) & 1)

    def __iter__(self):
        for item in range(self.limit):
            if item in self:
                yield item

    def __len__(self):
        return sum(1 for _ in self)

    def add(self, item):
        bytenum, bitnum = self._get_location(item)
        self.data[bytenum] |= (1 << bitnum)

    def discard(self, item):
        bytenum, bitnum = self._get_location(item)
        self.data[bytenum] &= ~(1 << bitnum)


    def _get_location(self, item):
        if item < 0 or item >= self.limit:
            raise ValueError(f"{item=} Must be in range 0 <= item < {self.limit}")

        return divmod(item, 8)

    def _from_iterable(self, iterable):
        return type(self)(self.limit, iterable)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(limit={self.limit}, iterable={list(self)})"

