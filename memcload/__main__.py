import glob
import gzip
import logging
import multiprocessing as mp
import os
import sys

from collections import Counter
from functools import partial
from optparse import OptionParser
from typing import Dict

import memcache

from . import appsinstalled_pb2
from .types import AppsInstalled, DeviceType, ProcessingStatus


NORMAL_ERR_RATE = 0.01


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def insert_appsinstalled(
    memc_addr: str, appsinstalled: AppsInstalled, dry_run: bool = False
) -> bool:
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type.value, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    try:
        if dry_run:
            logging.debug(
                "%s - %s -> %s" % (memc_addr, key, str(ua).replace("\n", " "))
            )
        else:
            memc = memcache.Client([memc_addr])
            memc.set(key, packed)
    except Exception as e:
        logging.exception("Cannot write to memc %s: %s" % (memc_addr, e))
        return False
    return True


def process_line(
    raw_line: bytes, device_memc: Dict[DeviceType, str], dry: bool
) -> ProcessingStatus:

    line = raw_line.decode("utf-8").strip()
    if not line:
        return ProcessingStatus.SKIP

    try:
        appsinstalled = AppsInstalled.from_raw(line)
    except ValueError as e:
        logging.error(f"Cannot parse line: {e}")
        return ProcessingStatus.ERROR

    memc_addr: str = device_memc[appsinstalled.dev_type]
    ok: bool = insert_appsinstalled(memc_addr, appsinstalled, dry)

    if not ok:
        return ProcessingStatus.ERROR

    return ProcessingStatus.OK


def check_memcached(options):
    """ Check if memcached is running.
    """
    addrs = {options.idfa, options.gaid, options.adid, options.dvid}
    for addr in addrs:
        client = memcache.Client([addr])
        key = "test:check_memcached"
        client.set(key, 42)
        if client.get(key) != 42:
            logging.error(f"Memcached on {addr} is not running.")
            sys.exit(1)
        client.delete(key)


def main(options):
    """ Entry point
    """
    device_memc: Dict[DeviceType, str] = {
        DeviceType.IDFA: options.idfa,
        DeviceType.GAID: options.gaid,
        DeviceType.ADID: options.adid,
        DeviceType.DVID: options.dvid,
    }

    for fn in glob.iglob(options.pattern):

        logging.info("Processing %s" % fn)

        with gzip.open(fn) as fd:
            with mp.Pool() as pool:
                job = partial(
                    process_line, device_memc=device_memc, dry=options.dry
                )
                statuses = Counter(
                    pool.imap_unordered(job, fd, chunksize=500)
                )

        ok = statuses[ProcessingStatus.OK]
        errors = statuses[ProcessingStatus.ERROR]
        processed = ok + errors

        if not processed:
            dot_rename(fn)
            continue

        err_rate = float(errors) / processed
        if err_rate < NORMAL_ERR_RATE:
            logging.info(
                "Acceptable error rate (%s). Successfull load" % err_rate
            )
        else:
            logging.error(
                "High error rate (%s > %s). Failed load"
                % (err_rate, NORMAL_ERR_RATE)
            )

        dot_rename(fn)


if __name__ == "__main__":
    op = OptionParser()

    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option(
        "--pattern", action="store", default="/data/appsinstalled/*.tsv.gz"
    )
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")

    (opts, args) = op.parse_args()

    if not opts.dry:
        check_memcached(opts)

    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO if not opts.dry else logging.DEBUG,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    logging.info("Memc loader started with options: %s" % opts)

    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
