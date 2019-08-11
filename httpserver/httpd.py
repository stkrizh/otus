import datetime as dt
import logging
import socket
import threading
import time

from typing import Tuple


from .types import HTTPMethod, HTTPRequest, HTTPResponse, HTTPStatus


BIND_ADDRESS = ("", 8080)
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
        status=HTTPStatus.OK, body=f"Method: {method}\nTarget: {target}\n\n"
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
        f"{response.body}",
    )

    try:
        conn.sendall("\r\n".join(data).encode("utf-8"))
    except socket.timeout:
        pass


def send_error(conn: socket.socket, status: HTTPStatus) -> None:
    """Send HTTP response with an error status code.
    """
    response = HTTPResponse(status=status, body="")
    send_response(conn, response)


def handle_client_connection(conn: socket.socket, addr: Tuple) -> None:
    """Handle an accepted client connection.
    """
    logging.debug(f"Connected by: {addr}")

    with conn:
        try:
            request = parse_request(conn)
            logging.info(f"{addr}: {request.method} {request.target}")
            response = handle_request(request)
        except HTTPException as exc:
            response = HTTPResponse(status=exc.args[0], body="")
            logging.info(f'{addr}: HTTP exception "{response.status}"')
        except Exception:
            logging.exception(f"{addr}: Unexpected error")
            response = HTTPResponse(
                status=HTTPStatus.INTERNAL_SERVER_ERROR, body=""
            )

        try:
            send_response(conn, response)
        except Exception:
            logging.exception(f"{addr}: Can't send a response")

    logging.debug(f"{addr}: connection closed")


def serve_forever(
    listening_socket: socket.socket, thread_id: int, run_event: threading.Event
) -> None:
    """Forever serve incoming connections on a listening socket.
    """
    logging.info(f"Worker-{thread_id} has been started")

    listening_socket.settimeout(1)

    while True:
        try:
            conn, addr = listening_socket.accept()
            handle_client_connection(conn, addr)
        except socket.timeout:
            if run_event.is_set():
                continue
            break

    logging.info(f"Worker-{thread_id} has been stopped")
    return None


def start_workers(n_workers: int = 4) -> None:
    """Forever serve incoming connections on a listening socket.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(BIND_ADDRESS)
        sock.listen(BACKLOG)

        run_event = threading.Event()
        run_event.set()

        pool = []
        for i in range(1, n_workers + 1):
            thread = threading.Thread(
                target=serve_forever, args=(sock, i, run_event)
            )
            pool.append(thread)
            thread.start()

        try:
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Server is stopping")
            run_event.clear()
            for worker in pool:
                worker.join()
