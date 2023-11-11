import re
from main import HTTP_201, HTTP_400, Loop, Request, Server


def handle_root(req: Request):
    resp = HTTP_400
    if req.method == "POST":
        print(f"POST: {req=}")
        resp = HTTP_201

    if req.method == "DELETE":
        print(f"DELETE: {req=}")
        resp = HTTP_201

    return resp + "\r\n\r\n"


handlers = [
    (lambda x: re.search(r"/(\S+)?", x) is not None, handle_root),
]

server = Server(loop=Loop(), handlers=handlers)
server.run()
