import math
import unittest

from . import appsinstalled_pb2
from .types import AppsInstalled, DeviceType


class TestMemcLoad(unittest.TestCase):
    def test_proto(self):
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
            self.assertEqual(ua, unpacked)

    def test_apps_installed_parse_valid(self):
        ap = AppsInstalled.from_raw("  idfa\t1\t0\t0\t1423,   ")
        self.assertIs(ap.dev_type, DeviceType.IDFA)
        self.assertEqual(ap.lat, 0)
        self.assertEqual(ap.lon, 0)
        self.assertEqual(len(ap.apps), 1)

        ap = AppsInstalled.from_raw("     gaid\t1\t-100\t-1000\t-1,0,1   ")
        self.assertIs(ap.dev_type, DeviceType.GAID)
        self.assertEqual(ap.lat, -100)
        self.assertEqual(ap.lon, -1000)
        self.assertEqual(len(ap.apps), 3)

        ap = AppsInstalled.from_raw("adid\t1\ta\tb\t      1,  2,  aaa, 42   ")
        self.assertIs(ap.dev_type, DeviceType.ADID)
        self.assertTrue(math.isnan(ap.lat))
        self.assertTrue(math.isnan(ap.lon))
        self.assertEqual(ap.apps, [1, 2, 42])

    def test_apps_installed_parse_invalid(self):
        with self.assertRaises(ValueError):
            AppsInstalled.from_raw("idfa\t1\t0\t0")

        with self.assertRaises(ValueError):
            AppsInstalled.from_raw("xxxx\t1\t0\t0\t1,2,3")

        with self.assertRaises(ValueError):
            AppsInstalled.from_raw("gaid\t\t0\t0\t1,2,3")


if __name__ == "__main__":
    unittest.main()
