import time

from litehttp import HTTP_201, HTTP_204, HTTP_400, Loop, Request, Server, json_response, text_response, stream_response


def handle_root(req: Request):
    if req.method == "GET":
        return text_response(text="Howdy!")

    if req.method == "POST":
        return json_response(data={'message': "created"}, status=HTTP_201)

    if req.method == "DELETE":
        return json_response(data={'message': "deleted"})

    if req.method == "PUT":
        return text_response(status=HTTP_204)

    return text_response(status=HTTP_400)


def sse_resp(req: Request):
    print("SSE: ", req)
    message = req.path.split("/")[-1]
    def stream():
        for _ in range(10):
            time.sleep(0.1)
            yield f"data: {message=}\r\n"

    return stream_response(stream())


handlers = [
    (lambda x: x == "/", handle_root),
    (lambda x: x.startswith("/sse/"), sse_resp),
]

server = Server(loop=Loop(), handlers=handlers)
server.run(port=5000)
