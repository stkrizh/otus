"""
Simple HTTP multithreaded server.

Serves static files in specified document root. Accepts GET and HEAD
HTTP methods.

Allowed file types:
.html | .js | .css |.jpeg | .jpg | .png | .gif | .swf

"""
import sys

from argparse import ArgumentParser
from pathlib import Path

from . import httpd
from .httpd import logging


def parse_args():
    """Parse command line arguments.
    """
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("-r", "--root", help="Document root.", required=True)
    parser.add_argument(
        "-w",
        "--workers",
        help="Number of workers [Default: 4].",
        default=4,
        type=int,
    )
    parser.add_argument(
        "-a",
        "--address",
        help="Server address [Default: 127.0.0.1]",
        default="127.0.0.1",
    )
    parser.add_argument(
        "-p",
        "--port",
        help="Listen port [Default: 8080]",
        default=8080,
        type=int,
    )

    return parser.parse_args()


args = parse_args()

n_workers = args.workers
if n_workers < 0:
    logging.error("Ivalid number of workers.")
    sys.exit()

document_root = Path(args.root)
if not document_root.is_dir():
    logging.error("Document root is not a directory.")
    sys.exit()

port = args.port
if port < 1:
    logging.error("Ivalid port to listen.")
    sys.exit()

httpd.serve_forever(args.address, port, document_root.resolve(), n_workers)
