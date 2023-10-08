import random
import time
import timeit
import functools
import typing as t
import inspect

def bench(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        t0 = time.perf_counter()
        ret = func(*args, **kwargs)
        t1 = time.perf_counter()
        print(f"[{func.__name__}] Took Time : {t1-t0}")
        return t1-t0
    return inner


def fn(x: int) -> int:
    count:int = 0
    for _ in range(x):
        count += 1
    return count


def cache(func):
    cached = {}
    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            return cached[args]
        except KeyError as ke:
            cached[args] = func(*args, **kwargs)
            return cached[args]
    return inner


@cache
def fn_cached(x: int) -> int:
    count:int = 0
    for _ in range(x):
        count += 1
    return count

l_b, h_b = int(1e6)-5, int(1e6)

@bench
def test(n: int):
    for _ in  range(n):
        n = random.randint(l_b, h_b)
        got = fn(n)
        assert(got == n)


@bench
def test_cached(n : int):
    for _ in  range(n):
        n = random.randint(l_b, h_b)
        got = fn_cached(n)
        assert(got == n)


should_bypass = False
print(f"{should_bypass=}")

def method_interceptor(func):
    @functools.wraps(func)
    def inner(*a, **kw):
        # print("method_interceptor", f"{func=}, {a=}, {kw=}")
        annotations = func.__annotations__
        # print(f"{annotations=}")
        rv = annotations.get('return')
        if not should_bypass:
            return func(*a, **kw)

        print(f"intercepted {func=}")
        return rv() if rv is not None else None

    return inner


def class_method_interceptor(interceptor, *args, **kw):
    def inner(cls):
        # print("class vars", cls, vars(cls))
        klass_props = vars(cls)
        # print("inner", args, kw)
        for name, member in klass_props.items():
            if name.startswith('__'):
                continue

            if callable(member):
                sig = inspect.signature(getattr(cls, name))
                params = sig.parameters
                if 'req_param' in params:
                    setattr(cls, name, interceptor(member))
            elif isinstance(member, (staticmethod,)): # classmethod,
                sig = inspect.signature(getattr(cls, name))
                params = sig.parameters
                if 'req_param' in params:
                    inner_func = member.__func__
                    method_type = type(member)
                    decorated = method_type(interceptor(inner_func))
                    setattr(cls, name, decorated)

        return cls

    return inner


T = t.TypeVar('T', bound='ToCache')

@class_method_interceptor(interceptor=method_interceptor)
class ToCache:
    def __init__(self, x, y=3):
        self.x = x
        self.y = y

    @staticmethod
    def static_method() -> str:
        print("[ToCache] static_method -> 'staticmethod'")
        return "staticmethod"

    @classmethod
    def class_method(cls: t.Type[T], x: int, y: int) -> T:
        print(f"[{cls.__name__}] class_method -> {cls}")
        return cls(x, y)

    @property
    def some_prop(self) -> int:
        print(f"[{self.__class__.__name__}] some_prop -> 2")
        return self.x * 2

    def compute(self, a: int) -> int:
        print(f"[{self.__class__.__name__}] compute(a) -> a ** a + self.y")
        return (a ** a) + self.y

    def is_bigger(self, a: int) -> bool:
        print(f"[{self.__class__.__name__}] is_bigger(a) -> a ** a + self.y > 3")
        return (a ** a) + self.y > 3

    def imp_method(self, req_param: int) -> bool:
        print(f"[{self.__class__.__name__}] imp_method(a) -> req_param > 0")
        return req_param > 0


def main() -> int:
    n = 30  # int(1e3)
    test(n)
    test_cached(n)
    tc = ToCache(5, y=4)
    print(tc.some_prop)
    print(tc.compute(3))
    print(tc.is_bigger(3))
    print(tc.imp_method(3))
    print(tc.static_method())
    print(tc.class_method(5, y=4))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())



"""
python3 -i decorator_test.py
>>> test(1000)
[test] Took Time : 39.68231679999735
39.68231679999735
>>> test_cached(1000)
[test_cached] Took Time : 0.0014149999478831887
0.0014149999478831887
"""
