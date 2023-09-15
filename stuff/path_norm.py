input_p = "/home/ssam/../folder1/././../folder2/file.sh"

def path_sep(x: str) -> bool:
  return x == '/'

def get_tokens(inp):
  token = ""
  got_sep = False
  for char in (inp + '/.'):
    if path_sep(char):
      got_sep = True
    else:
      if got_sep:
        yield token
        got_sep = False
        token = ""
      token += char

def curr_ref(x: str) -> bool:
  return x == '.'

def parent_ref(x: str) -> bool:
  return x == '..'

res = []
for token in get_tokens(input_p.lstrip('/')):
  if curr_ref(token):
    pass
  elif parent_ref(token):
    if len(res) > 0:
      res.pop()
  else:
    res.append(token)

ans = '/' + '/'.join(res)
print(f"{input_p=}, {ans=}")
