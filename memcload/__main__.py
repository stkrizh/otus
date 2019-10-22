import glob
import gzip
import logging
import multiprocessing as mp
import os
import sys
import time

from collections import Counter
from functools import partial
from optparse import OptionParser
from pathlib import Path
from typing import List

import memcache

from . import appsinstalled_pb2
from .types import AppsInstalled, ProcessingStatus


NORMAL_ERR_RATE = 0.01
MEMCACHE_RETRY_NUMBER = 3
MEMCACHE_RETRY_TIMEOUT_SECONDS = 1
MEMCACHE_SOCKET_TIMEOUT_SECONDS = 3


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def insert_appsinstalled(
    memcache_client: memcache.Client,
    appsinstalled: AppsInstalled,
    dry_run: bool = False,
) -> bool:
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()

    if dry_run:
        logging.debug("%s -> %s" % (key, str(ua).replace("\n", " ")))
        return True

    for _ in range(MEMCACHE_RETRY_NUMBER):
        try:
            # Use a tuple as key to write to specific Memcached server
            # https://github.com/linsomniac/python-memcached/blob/bad41222379102e3f18f6f2f7be3ee608de6fbff/memcache.py#L698
            success: bool = memcache_client.set(
                (appsinstalled.dev_type.value, key), packed
            )
        except Exception as e:
            logging.exception(f"Cannot write to Memcache: {e}")
            return False
        if success:
            return True
        time.sleep(MEMCACHE_RETRY_TIMEOUT_SECONDS)

    logging.error("Cannot write to Memcache. Server is down")
    return False


def process_line(
    raw_line: bytes, memcache_client: memcache.Client, dry: bool
) -> ProcessingStatus:

    line = raw_line.decode("utf-8").strip()
    if not line:
        return ProcessingStatus.SKIP

    try:
        appsinstalled = AppsInstalled.from_raw(line)
    except ValueError as e:
        logging.error(f"Cannot parse line: {e}")
        return ProcessingStatus.ERROR

    ok: bool = insert_appsinstalled(memcache_client, appsinstalled, dry)
    if not ok:
        return ProcessingStatus.ERROR

    return ProcessingStatus.OK


def process_file(fn: str, memcache_addresses: List[str], dry: bool) -> None:
    worker = mp.current_process()
    logging.info(f"[{worker.name}] Processing {fn}")

    memcache_client = memcache.Client(
        memcache_addresses,
        socket_timeout=3,
        dead_retry=MEMCACHE_RETRY_TIMEOUT_SECONDS,
    )
    with gzip.open(fn) as fd:
        job = partial(process_line, memcache_client=memcache_client, dry=dry)
        statuses = Counter(map(job, fd))

    ok = statuses[ProcessingStatus.OK]
    errors = statuses[ProcessingStatus.ERROR]
    processed = ok + errors

    err_rate = float(errors) / processed if processed else 1.0

    if err_rate < NORMAL_ERR_RATE:
        logging.info(
            f"[{worker.name}] [{fn}] Acceptable error rate: {err_rate}."
            f" Successfull load"
        )
    else:
        logging.error(
            f"[{worker.name}] [{fn}] High error rate: "
            f"{err_rate} > {NORMAL_ERR_RATE}. Failed load"
        )

    return fn


def main(options):
    """ Entry point
    """
    memcache_addresses: List[str] = [
        options.idfa,
        options.gaid,
        options.adid,
        options.dvid,
    ]

    job = partial(
        process_file, memcache_addresses=memcache_addresses, dry=options.dry
    )

    files = sorted(
        glob.glob(options.pattern), key=lambda file: Path(file).name
    )

    with mp.Pool() as pool:
        for processed_file in pool.imap(job, files):
            worker = mp.current_process()
            logging.info(f"[{worker.name}] Renaming {processed_file}")
            dot_rename(processed_file)


if __name__ == "__main__":
    op = OptionParser()

    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--loglevel", action="store", default="INFO")
    op.add_option(
        "--pattern", action="store", default="/data/appsinstalled/*.tsv.gz"
    )
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")

    (opts, args) = op.parse_args()

    logging.basicConfig(
        filename=opts.log,
        level=getattr(logging, opts.loglevel, logging.INFO),
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    logging.info("Memc loader started with options: %s" % opts)

    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
