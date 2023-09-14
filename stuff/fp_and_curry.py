from collections import namedtuple

Pair = namedtuple('Pair', ['first', 'second'])

def pair(x):
    def fn(y):
        return Pair(x, y)
    return fn

print(pair(10)(20))

def head(pair):
    return pair.first

def tail(pair):
    return pair.second

def range(left):
    def fn(right):
        if left > right:
            return None
        return Pair(left, range(left + 1)(right))
    return fn


xs_5 = range(1)(5)
print(f"{xs_5=}")

# impure because mutates nonlocal array
def list_to_array(xs):
    rv = []
    def inner(xs):
        nonlocal rv
        if xs is None:
            return rv
        rv.append(head(xs))
        return inner(tail(xs))

    return inner(xs)

# impure since accepts array?
def array_to_list(array):
    def inner(array):
        def _inner(rv=None):
            if len(array) == 0:
                return rv
            return inner(array[1:])(Pair(array[0], rv))
        return _inner

    return inner(array)()


def mmap(func):
    def inner(xs):
        if xs is None:
            return None
        return Pair(func(head(xs)), mmap(func)( tail(xs) ))
    return inner

print(f"{list_to_array(xs_5)=}")
print(f"{array_to_list(list_to_array(xs_5))=}")

print(f"{list_to_array(mmap(lambda x: x*x) (xs_5))=}")


fxs = range(1)(100)

def fizzBuzz(x):
    if x % 15 == 0:
        return "FizzBuzz"
    elif x % 3 == 0:
        return "Fizz"
    elif x % 5 == 0:
        return "Buzz"
    return x

print(f"{list_to_array(mmap(fizzBuzz) (fxs))=}")


def inf_curry(arg=None):
    items = []
    def inner(a=None):
        nonlocal items
        if a is None:
            return items

        items.append(a)
        return inner

    return inner(arg)


print(f"{inf_curry()=}")
print(f"{inf_curry(1)()=}")
print(f"{inf_curry(1)(2)(3)(4)(5)()=}")
# print(f"{inf_curry(1,2)()=}")


def mfilter(func):
    def inner(xs):
        if xs is None:
            return None
        if func(head(xs)) is True:
            return Pair(head(xs), mfilter(func)(tail(xs)))

        return mfilter(func)(tail(xs))
    return inner

xs_10 = range(1)(10)
print(f"{list_to_array(mfilter(lambda x: x % 2 == 0)(xs_10))=}")


def take(xs):
    def inner(n):
        if n <= 0:
            return None
        return Pair(head(xs), take(tail(xs))(n-1))
    return inner

print(f"{list_to_array(take(xs_10)(4))=}")


print(f"{list_to_array(take( mfilter(lambda x: x%2 == 1)(xs_10))(3))=}")


def sieve(xs):
    """
    ref - https://en.wikipedia.org/wiki/Sieve_of_Eratosthenes
    """
    if xs is None:
        return None

    return Pair(
            head(xs),
            sieve( mfilter(lambda x: x % head(xs) != 0)(tail(xs)) )
        )


xs_2_60 = range(2)(60)
print(f"{list_to_array(sieve(xs_2_60))=}")


def mersenne(xs):
    """
    https://en.wikipedia.org/wiki/Mersenne_prime
    mersenne primes - any prime of the form 2**n - 1
    """
    if xs is None:
        return None

    return Pair(
            head(xs),
            mersenne(mfilter(lambda x: x & (x+1) == 0)(tail(xs)))
        )

xs_3_200 = range(3)(200)
print(f"{list_to_array(mersenne(sieve(xs_3_200)))=}")


# TODO: maybe actually make the `Pair` lazy where the tail is itself 
# a function which needs to be called to be evaluated.


"""
Pair(first=10, second=20)

xs_5=Pair(first=1, second=Pair(first=2, second=Pair(first=3,
second=Pair(first=4, second=Pair(first=5, second=None)))))

list_to_array(xs_5)=[1, 2, 3, 4, 5]

array_to_list(list_to_array(xs_5))=Pair(first=1, second=Pair(first=2,
second=Pair(first=3, second=Pair(first=4, second=Pair(first=5, second=None)))))

list_to_array(mmap(lambda x: x*x) (xs_5))=[1, 4, 9, 16, 25]

list_to_array(mmap(fizzBuzz) (fxs))=[1, 2, 'Fizz', 4, 'Buzz', 'Fizz', 7, 8,
'Fizz', 'Buzz', 11, 'Fizz', 13, 14, 'FizzBuzz', 16, 17, 'Fizz', 19, 'Buzz',
'Fizz', 22, 23, 'Fizz', 'Buzz', 26, 'Fizz', 28, 29, 'FizzBuzz', 31, 32, 'Fizz',
34, 'Buzz', 'Fizz', 37, 38, 'Fizz', 'Buzz', 41, 'Fizz', 43, 44, 'FizzBuzz', 46,
47, 'Fizz', 49, 'Buzz', 'Fizz', 52, 53, 'Fizz', 'Buzz', 56, 'Fizz', 58, 59,
'FizzBuzz', 61, 62, 'Fizz', 64, 'Buzz', 'Fizz', 67, 68, 'Fizz', 'Buzz', 71,
'Fizz', 73, 74, 'FizzBuzz', 76, 77, 'Fizz', 79, 'Buzz', 'Fizz', 82, 83, 'Fizz',
'Buzz', 86, 'Fizz', 88, 89, 'FizzBuzz', 91, 92, 'Fizz', 94, 'Buzz', 'Fizz', 97,
98, 'Fizz', 'Buzz']

inf_curry()=[]
inf_curry(1)()=[1]
inf_curry(1)(2)(3)(4)(5)()=[1, 2, 3, 4, 5]

list_to_array(mfilter(lambda x: x % 2 == 0)(xs_10))=[2, 4, 6, 8, 10]

list_to_array(take(xs_10)(4))=[1, 2, 3, 4]

list_to_array(take( mfilter(lambda x: x%2 == 1)(xs_10))(3))=[1, 3, 5]

list_to_array(sieve(xs_2_60))=[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41,
43, 47, 53, 59]

list_to_array(mersenne(sieve(xs_3_200)))=[3, 7, 31, 127] 
"""
