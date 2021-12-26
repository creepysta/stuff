row, col = 7, 7
cen = row // 2
moves = set()
board = [[-1] * row for _ in range(row)]
dirs = [(-1, 0), (0, 1), (0, -1), (1, 0)]

def valid(i, j):
  global valids
  return (i, j) in moves #(and 0 <= i < row and 0 <= j < col)

def check(y, x, dy, dx):
  # check current pos
  # check 1 in next cell in the given dir
  # check 0 in next to next cell in the given dir
  if valid(y, x):
    nx, ny = x + dx, y + dy
    if valid(ny, nx) and board[y][x] == 1:
      if board[ny][nx] == 1:
        nnx, nny = nx + dx, ny + dy
        if valid(nny, nnx):
          if board[nny][nnx] == 0:
            return True
  return False

def display(board):
  for y in range(row):
    for x in range(col):
      if valid(y, x):
        if board[y][x] == 1:
          print('%2s' % ('O'), end = ' \n'[x == col-1])
        elif board[y][x] == 0:
          print('%2s' % ('_'), end = ' \n'[x == col-1])
        elif board[y][x] == -1:
          print('%2s' % (' '), end = ' \n'[x == col-1])
        else:
          print('%2s' % (board[y][x]), end = ' \n'[x == col-1])
      else:
        print('  ', end = ' \n'[x == col-1])
  input("press Enter> ")

def solver(board):
  global dirs, moves
  ones = 0
  for y in range(row):
    for x in range(col):
      if valid(y, x):
        ones += board[y][x]
  if ones == 1:
    print("GOT IT")
    display(board)
    exit()
  for y, x in moves:
    for dy, dx in dirs:
      if check(y, x, dy, dx):
        b1 = [x[:] for x in board]
        board[y][x] = board[y+dy][x+dx] = 0
        board[y+2*dy][x+2*dx] = 1
        b1[y][x] , b1[y+dy][x+dx] = '_', 'x'
        b1[y+2*dy][x+2*dx] = 'O'
        display(b1)
        solver(board)
        board[y][x] = board[y+dy][x+dx] = 1
        board[y+2*dy][x+2*dx] = 0
        b1[y][x] , b1[y+dy][x+dx] = 1, 1
        b1[y+2*dy][x+2*dx] = 0
        display(b1)

if __name__ == "__main__":
  for i in range(row):
    for j in range(3):
      moves.add((i, 2+j))
      board[i][2+j] = 1

  for i in range(3):
    for j in range(col):
      moves.add((2+i, j))
      board[2+i][j] = 1
  board[cen][cen] = 0
  board = [[0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0],
      [0,0,1,0,1,0,0],
      [0,0,1,1,1,0,0],
      [0,0,1,1,1,0,0],
      [0,0,1,1,1,0,0]]
  display(board)
  print(sorted(moves))
  solver(board)
