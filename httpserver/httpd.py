import datetime as dt
import logging
import socket


from .types import HTTPMethod, HTTPRequest, HTTPResponse, HTTPStatus


BIND_ADDRESS = ("", 8000)
BACKLOG = 10


REQUEST_SOCKET_TIMEOUT = 10
REQUEST_MAX_SIZE = 8 * 1024


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname).1s %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)


class HTTPException(Exception):
    pass


def parse_request(conn: socket.socket) -> HTTPRequest:
    """Read data from client socket and parse the request.
    """
    conn.settimeout(REQUEST_SOCKET_TIMEOUT)

    try:
        data = conn.recv(REQUEST_MAX_SIZE)
    except socket.timeout:
        raise HTTPException(HTTPStatus.REQUEST_TIMEOUT)

    raw_request_line, *_ = data.partition(b"\r\n")
    request_line = str(raw_request_line, "iso-8859-1")

    try:
        raw_method, target, version = request_line.split()
    except ValueError:
        raise HTTPException(HTTPStatus.BAD_REQUEST)

    if version != "HTTP/1.1":
        raise HTTPException(HTTPStatus.HTTP_VERSION_NOT_SUPPORTED)

    try:
        method = HTTPMethod[raw_method]
    except KeyError:
        raise HTTPException(HTTPStatus.METHOD_NOT_ALLOWED)

    return HTTPRequest(method=method, target=target)


def handle_request(request: HTTPRequest) -> HTTPResponse:
    """Process request.
    """
    method, target = request
    response = HTTPResponse(
        status=HTTPStatus.OK,
        body=f"Method: {method}\nTarget: {target}\n\n"
    )
    return response


def send_response(conn: socket.socket, response: HTTPResponse) -> None:
    """Send HTTP response.
    """
    now = dt.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    data = (
        f"HTTP/1.1 {response.status}",
        f"Date: {now}",
        f"Content-Type: text/plain; charset=UTF-8",
        f"Server: Fancy Python HTTP Server",
        f"Connection: close",
        f"",
        f"{response.body}"
    )

    conn.sendall("\r\n".join(data).encode("utf-8"))


def send_error(conn: socket.socket, status: HTTPStatus) -> None:
    """Send HTTP response with error.
    """
    response = HTTPResponse(
        status=status,
        body=""
    )
    send_response(conn, response)


def serve_forever() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(BIND_ADDRESS)
        s.listen()

        try:
            while True:
                conn, addr = s.accept()
                logging.info(f"Connected by: {addr}")

                with conn:
                    try:
                        request = parse_request(conn)
                        response = handle_request(request)
                        send_response(conn, response)
                    except HTTPException as exc:
                        status = exc.args[0]
                        logging.info(f"Error: {status} for {addr}")
                        send_error(conn, status)
                    except Exception:
                        logging.exception()
                        send_error(conn, HTTPStatus.INTERNAL_SERVER_ERROR)

        except KeyboardInterrupt:
            logging.info("Interrupted by user")
            return None
