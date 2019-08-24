import datetime as dt
import logging
import socket
import threading
import time
import urllib.parse

from pathlib import Path
from typing import Tuple

from .types import HTTPMethod, HTTPRequest, HTTPResponse, HTTPStatus


ALLOWED_CONTENT_TYPES = {
    ".html": "text/html",
    ".js": "application/javascript",
    ".css": "text/css",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".swf": "application/x-shockwave-flash",
    ".txt": "text/plain",
}
BACKLOG = 10
REQUEST_SOCKET_TIMEOUT = 10
REQUEST_CHUNK_SIZE = 1024
REQUEST_MAX_SIZE = 8 * 1024


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname).1s %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)


class HTTPException(Exception):
    pass


def receive(conn: socket.socket) -> bytearray:
    """Read raw bytes from a client socket.
    """
    conn.settimeout(REQUEST_SOCKET_TIMEOUT)

    try:
        received = bytearray()

        while True:
            if len(received) > REQUEST_MAX_SIZE:
                break

            if b"\r\n\r\n" in received:
                break

            chunk = conn.recv(REQUEST_CHUNK_SIZE)
            if not chunk:
                break

            received += chunk

    except socket.timeout:
        raise HTTPException(HTTPStatus.REQUEST_TIMEOUT)

    return received


def parse_request(received: bytearray) -> HTTPRequest:
    """Parse request from raw bytes received from a client.
    """
    raw_request_line, *_ = received.partition(b"\r\n")
    request_line = str(raw_request_line, "iso-8859-1")

    try:
        raw_method, raw_target, version = request_line.split()
    except ValueError:
        raise HTTPException(HTTPStatus.BAD_REQUEST)

    try:
        method = HTTPMethod[raw_method]
    except KeyError:
        raise HTTPException(HTTPStatus.METHOD_NOT_ALLOWED)

    return HTTPRequest(method=method, target=urllib.parse.unquote(raw_target))


def handle_request(request: HTTPRequest, document_root: Path) -> HTTPResponse:
    """Process request.
    """
    method = request.method
    target = request.clean_target()

    path = Path(document_root, target).resolve()

    # Probably it's a pointless part due to pathlib removes trailing slashes
    if path.is_file() and target.endswith("/"):
        return HTTPResponse.error(HTTPStatus.NOT_FOUND)

    if path.is_dir():
        path /= "index.html"

    # Prevent access to parents of the root directory
    if document_root not in path.parents:
        return HTTPResponse.error(HTTPStatus.FORBIDDEN)

    if not path.is_file():
        return HTTPResponse.error(HTTPStatus.NOT_FOUND)

    if path.suffix not in ALLOWED_CONTENT_TYPES:
        return HTTPResponse.error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    stat = path.stat()
    content_length = stat.st_size
    body = b"" if method is HTTPMethod.HEAD else path.read_bytes()

    return HTTPResponse(
        status=HTTPStatus.OK,
        body=body,
        content_type=ALLOWED_CONTENT_TYPES[path.suffix],
        content_length=content_length,
    )


def send_response(conn: socket.socket, response: HTTPResponse) -> None:
    """Send HTTP response.
    """
    now = dt.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    headers = (
        f"HTTP/1.1 {response.status}",
        f"Date: {now}",
        f"Content-Type: {response.content_type}",
        f"Content-Length: {response.content_length}",
        f"Server: Fancy-Python-HTTP-Server",
        f"Connection: close",
        f"",
    )

    try:
        raw_response: bytes = "\r\n".join(headers).encode("utf-8")
        raw_response += b"\r\n" + response.body
        conn.sendall(raw_response)
    except socket.timeout:
        pass


def send_error(conn: socket.socket, status: HTTPStatus) -> None:
    """Send HTTP response with an error status code.
    """
    response = HTTPResponse.error(status)
    send_response(conn, response)


def handle_client_connection(
    conn: socket.socket, addr: Tuple, document_root: Path
) -> None:
    """Handle an accepted client connection.
    """
    logging.debug(f"Connected by: {addr}.")

    with conn:
        try:
            raw_bytes = receive(conn)
            request = parse_request(raw_bytes)
            response = handle_request(request, document_root)
            logging.info(f"{addr}: {request.method} {request.target}")
        except HTTPException as exc:
            status = exc.args[0]
            response = HTTPResponse.error(status)
            logging.info(f'{addr}: HTTP exception "{response.status}".')
        except Exception:
            logging.exception(f"{addr}: Unexpected error.")
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            response = HTTPResponse.error(status)

        try:
            send_response(conn, response)
        except Exception:
            logging.exception(f"{addr}: Can't send a response.")

    logging.debug(f"{addr}: connection closed.")


def wait_connection(
    listening_socket: socket.socket, thread_id: int, document_root: Path
) -> None:
    """Forever serve incoming connections on a listening socket.
    """
    logging.debug(f"Worker-{thread_id} has been started.")

    while True:
        conn, addr = listening_socket.accept()
        handle_client_connection(conn, addr, document_root)

    logging.debug(f"Worker-{thread_id} has been stopped.")
    return None


def serve_forever(
    address: str, port: int, document_root: Path, n_workers: int
) -> None:
    """Open a listener socket and start workers in separate threads.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            sock.bind((address, port))
        except PermissionError:
            logging.error(f"Permission denied: {address}:{port}")
            return None
        except OSError:
            logging.error(f"Invalid address / port: {address}:{port}")
            return None

        sock.listen(BACKLOG)

        for i in range(1, n_workers + 1):
            thread = threading.Thread(
                target=wait_connection, args=(sock, i, document_root)
            )
            thread.daemon = True
            thread.start()

        logging.info(
            f"Running on http://{address}:{port}/ (Press CTRL+C to quit)"
        )

        try:
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Server is stopping.")
            return None
