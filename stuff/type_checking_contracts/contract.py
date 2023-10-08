# The Fun of Reinvention (Screencast)
# https://www.youtube.com/watch?v=js_0wjzuMfc&ab_channel=DavidBeazley

from inspect import signature
from functools import wraps
from collections import ChainMap
from typing import Callable


_contracts = {}
class Contract:

  @classmethod
  def __init_subclass__(cls):
    _contracts[cls.__name__] = cls

  def __set__(self, instance, val):
    self.check(val)
    instance.__dict__[self.name] = val

  # https://docs.python.org/3/howto/descriptor.html "Customized names"
  def __set_name__(self, owner, name):
    self.name = name

  @classmethod
  def check(cls, val):
    pass

class Typed(Contract):
  _type = None

  @classmethod
  def check(cls, val):
    assert cls._type is not None, f"Type can't be None"
    assert isinstance(val, cls._type), f'Expected {cls._type}'
    super().check(val)

class Positive(Contract):
  @classmethod
  def check(cls, val):
    assert val > 0, "Expected > 0"
    super().check(val)

class NonEmpty(Contract):
  @classmethod
  def check(cls, val):
    assert len(val) > 0, "Expected Non Empty"
    super().check(val)

class Integer(Typed):
  _type = int

class String(Typed):
  _type = str

# MRO :- http://python-history.blogspot.com/2010/06/method-resolution-order.html
class NonEmptyString(String, NonEmpty):
  pass

class PositiveInteger(Integer, Positive):
  pass


def checked(func: Callable):
  sig = signature(func)
  # ann = func.__annotations__
  # this makes it possible to use typemaps (module level annotations)
  # in `player.py` where the `top` and `down` methods can't still have type
  # checks enabled
  ann = ChainMap(
      func.__annotations__,
      func.__globals__.get('__annotations__', {})
    )

  @wraps(func)
  def wrapper(*args, **kwargs):
    bound = sig.bind(*args, **kwargs)
    for name, val in bound.arguments.items():
      if name in ann:
        ann[name].check(val)
    return func(*args, **kwargs)

  return wrapper

@checked
def gcd(a: PositiveInteger, b: PositiveInteger):
  '''
  Compute greatest common divisor
  '''
  while b:
    a, b = b, a % b

  return a

class Player1:
  name = NonEmptyString()
  x = Integer()
  y = Integer()

  def __init__(self, name, x, y):
    self.name = name
    self.x = x
    self.y = y

  def left(self, dx):
    self.x -= dx

  def right(self, dx):
    self.x += dx


class BaseMeta(type):
  # in player.py, the file doesn't need to import the types anymore
  @classmethod
  def __prepare__(cls, *args):
    return ChainMap({}, _contracts)

  def __new__(cls, name, bases, methods):
    methods = methods.maps[0]
    return super().__new__(cls, name, bases, methods)


class Base(metaclass=BaseMeta):
  @classmethod
  def __init_subclass__(cls):
    # Apply checked decorator
    for name, val in vars(cls).items():
      if callable(val):
        setattr(cls, name, checked(val))

    # Instantiate contracts
    for name, val in cls.__annotations__.items():
      contract = val()  # Similar to name = Integer() in Player1 class
      contract.__set_name__(cls, name)
      setattr(cls, name, contract)

  def __init__(self, *args):
    ann = self.__annotations__
    assert len(args) == len(ann), f"Expected {len(ann)} arguments"

    for name, val in zip(ann, args):
      setattr(self, name, val)

  def __repr__(self):
    args = ','.join(
        repr(getattr(self, name))
        for name in self.__annotations__
      )
    return f'{type(self).__name__}({args})'

