#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import sys
import glob
import logging
import multiprocessing as mp
from collections import Counter
from enum import Enum
from functools import partial
from optparse import OptionParser
from typing import Dict, List, NamedTuple

# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
from . import appsinstalled_pb2

# pip install python-memcached
import memcache

NORMAL_ERR_RATE = 0.01


class DeviceType(Enum):
    IDFA = "idfa"
    GAID = "gaid"
    ADID = "adid"
    DVID = "dvid"


class ProcessingStatus(Enum):
    OK = 1
    ERROR = -1
    SKIP = 0


class AppsInstalled(NamedTuple):
    dev_type: DeviceType
    dev_id: str
    lat: float
    lon: float
    apps: List[int]

    @classmethod
    def from_raw(cls, line: str) -> "AppsInstalled":
        line_parts = line.strip().split("\t")

        if len(line_parts) < 5:
            raise ValueError("Invalid format.")

        raw_dev_type, dev_id, raw_lat, raw_lon, raw_apps = line_parts

        try:
            raw_dev_type = raw_dev_type.strip().lower()
            dev_type = DeviceType(raw_dev_type)
        except ValueError:
            raise ValueError(f"Unknown device type: {raw_dev_type}")

        if not dev_id:
            raise ValueError("Device ID missed.")

        try:
            apps = [int(a.strip()) for a in raw_apps.split(",")]
        except ValueError:
            apps = [
                int(a.strip()) for a in raw_apps.split(",") if a.isdigit()
            ]
            logging.info("Not all user apps are digits: `%s`" % line)

        try:
            lat, lon = float(raw_lat), float(raw_lon)
        except ValueError:
            logging.info("Invalid geo coords: `%s`" % line)

        return cls(dev_type, dev_id, lat, lon, apps)


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
    # @TODO persistent connection
    # @TODO retry and timeouts!
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


def prototest():
    sample = (
        "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\n"
        "gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    )
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == "__main__":
    op = OptionParser()

    op.add_option("-t", "--test", action="store_true", default=False)
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

    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO if not opts.dry else logging.DEBUG,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)

    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
