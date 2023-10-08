"""
Importing the other types for annotations are not required because of
`BaseMeta` class handling all the types in its __prepare__ method with
a ChainMap
"""

from contract import Base, PositiveInteger

# the `checked` decorator captures the globals for a function and handles the
# annotations, that's why module level annotations will also work for
# methods `top` and `down`

# typemap
dy: PositiveInteger

class Player2(Base):
  name: NonEmptyString
  x: Integer
  y: Integer

  def left(self, dx: PositiveInteger):
    self.x -= dx

  def right(self, dx: PositiveInteger):
    self.x += dx

  def top(self, dy):
    self.y -= dy

  def down(self, dy):
    self.y += dy

