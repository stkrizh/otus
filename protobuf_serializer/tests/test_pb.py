import gzip
import os
import struct
import unittest

import pb

MAGIC = 0xFFFFFFFF
DEVICE_APPS_TYPE = 1
TEST_FILE = "test.pb.gz"


class TestPB(unittest.TestCase):
    deviceapps = [
        {
            "device": {
                "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d",
                "type": "idfa",
            },
            "lat": 67.7835424444,
            "lon": 32.4561231233,
            "apps": [1, 2, 3],
        },
        {
            "device": {
                "type": "gaid",
                "id": "e7e1a50c0ec2747ca56cd9e1558c0d7d",
            },
            "apps": [1],
        },
    ]

    def assertMessagesEqual(self, msg_1: dict, msg_2: dict) -> bool:
        self.assertEqual(msg_1.get("device", {}), msg_2.get("device", {}))
        self.assertEqual(msg_1.get("lat"), msg_2.get("lat"))
        self.assertEqual(msg_1.get("lon"), msg_2.get("lon"))
        self.assertEqual(msg_1.get("apps", []), msg_2.get("apps", []))

    def tearDown(self):
        os.remove(TEST_FILE)
        # pass

    def test_write(self):
        bytes_written = pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)
        self.assertTrue(bytes_written > 0)

    def test_header(self):
        pb.deviceapps_xwrite_pb(self.deviceapps, TEST_FILE)

        with gzip.open(TEST_FILE, "rb") as f:
            content = f.read()

        self.assertTrue(isinstance(content, bytes))

        # First message
        magic, device_apps_type, length = struct.unpack("IHH", content[:8])
        self.assertEqual((MAGIC, DEVICE_APPS_TYPE), (magic, device_apps_type))

        # Second message
        offset = 8 + length
        magic, device_apps_type, length = struct.unpack(
            "IHH", content[offset : (offset + 8)]
        )
        self.assertEqual((MAGIC, DEVICE_APPS_TYPE), (magic, device_apps_type))
        self.assertEqual(len(content), offset + 8 + length)

    def test_empty_list(self):
        messages = []

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertEqual(0, bytes_written)
        self.assertTrue(os.path.isfile(TEST_FILE))

    def test_list_with_invalid_messages(self):
        messages = [1, 2, 3]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertEqual(0, bytes_written)
        self.assertTrue(os.path.isfile(TEST_FILE))

    def test_empty_messages(self):
        messages = [{}, {}, {}]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertTrue(bytes_written > 0)
        self.assertTrue(os.path.isfile(TEST_FILE))

        unpacked = list(pb.deviceapps_xread_pb(TEST_FILE))

        self.assertEqual(len(unpacked), 3)
        for m1, m2 in zip(messages, unpacked):
            self.assertMessagesEqual(m1, m2)

    def test_empty_device(self):
        messages = [{"lat": 2.314141, "lon": 5.66523423}]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertTrue(bytes_written > 0)
        self.assertTrue(os.path.isfile(TEST_FILE))

        unpacked = list(pb.deviceapps_xread_pb(TEST_FILE))

        self.assertEqual(len(unpacked), 1)
        for m1, m2 in zip(messages, unpacked):
            self.assertMessagesEqual(m1, m2)

    def test_device_empty_dict(self):
        messages = [{"device": {}, "lat": 2.314141, "lon": 5.66523423}]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertTrue(bytes_written > 0)
        self.assertTrue(os.path.isfile(TEST_FILE))

        unpacked = list(pb.deviceapps_xread_pb(TEST_FILE))

        self.assertEqual(len(unpacked), 1)
        for m1, m2 in zip(messages, unpacked):
            self.assertMessagesEqual(m1, m2)

    def test_invalid_device(self):
        messages = [{"device": 123}]

        with self.assertRaises(Exception) as err:
            pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertEqual("Could not serialize the data.", str(err.exception))

    def test_invalid_device_keys(self):
        messages = [{"device": {"foo": 42, "bar": 777}}]
        expected = [{"device": {}}]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertTrue(bytes_written > 0)
        self.assertTrue(os.path.isfile(TEST_FILE))

        unpacked = list(pb.deviceapps_xread_pb(TEST_FILE))

        self.assertEqual(len(unpacked), 1)
        for m1, m2 in zip(expected, unpacked):
            self.assertMessagesEqual(m1, m2)

    def test_invalid_device_id(self):
        messages = [{"device": {"id": 42}}]

        with self.assertRaises(Exception) as err:
            pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertEqual("Could not serialize the data.", str(err.exception))

    def test_invalid_device_type(self):
        messages = [{"device": {"type": None}}]

        with self.assertRaises(Exception) as err:
            pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertEqual("Could not serialize the data.", str(err.exception))

    def test_valid_device(self):
        messages = [
            {"device": {"id": ""}},
            {"device": {"type": ""}},
            {"device": {"id": "123", "type": "idfa"}},
            {"device": {"id": "123", "type": "idfa"}},
        ]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertTrue(bytes_written > 0)
        self.assertTrue(os.path.isfile(TEST_FILE))

        unpacked = list(pb.deviceapps_xread_pb(TEST_FILE))

        self.assertEqual(len(messages), len(unpacked))
        for m1, m2 in zip(messages, unpacked):
            self.assertMessagesEqual(m1, m2)

    def test_invalid_lat(self):
        messages = [{"lat": "invalid"}]

        with self.assertRaises(Exception) as err:
            pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertEqual("Could not serialize the data.", str(err.exception))

    def test_invalid_lon(self):
        messages = [{"lon": "invalid"}]

        with self.assertRaises(Exception) as err:
            pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertEqual("Could not serialize the data.", str(err.exception))

    def test_valid_coordinates(self):
        messages = [
            {"lat": 0},
            {"lon": 0},
            {"lat": 0, "lon": 0},
            {"lat": 42, "lon": 42},
            {"lat": -42.123123123, "lon": 42.123213},
        ]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertTrue(bytes_written > 0)
        self.assertTrue(os.path.isfile(TEST_FILE))

        unpacked = list(pb.deviceapps_xread_pb(TEST_FILE))

        self.assertEqual(len(messages), len(unpacked))
        for m1, m2 in zip(messages, unpacked):
            self.assertMessagesEqual(m1, m2)

    def test_empty_apps(self):
        messages = [{"device": {"id": "123"}, "lat": 2.314, "lon": 5.665}]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertTrue(bytes_written > 0)
        self.assertTrue(os.path.isfile(TEST_FILE))

        unpacked = list(pb.deviceapps_xread_pb(TEST_FILE))

        self.assertEqual(len(unpacked), 1)
        for m1, m2 in zip(messages, unpacked):
            self.assertMessagesEqual(m1, m2)

    def test_apps_empty_list(self):
        messages = [{"apps": [], "lat": 2.314141, "lon": 5.66523423}]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertTrue(bytes_written > 0)
        self.assertTrue(os.path.isfile(TEST_FILE))

        unpacked = list(pb.deviceapps_xread_pb(TEST_FILE))

        self.assertEqual(len(unpacked), 1)
        for m1, m2 in zip(messages, unpacked):
            self.assertMessagesEqual(m1, m2)

    def test_ivalid_apps(self):
        messages = [{"apps": "invalid", "lat": 2.314141, "lon": 5.66523423}]

        with self.assertRaises(Exception) as err:
            pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertEqual("Could not serialize the data.", str(err.exception))

    def test_valid_apps(self):
        messages = [
            {"apps": [0]},
            {"apps": [None, "aaa", []]},
            {"apps": ["1", 2, 3.0, "4", None, 5]},
            {"apps": [-(2**64), -1, 1, 2**32 - 1, 2**32, 2**64]},
        ]

        expected = [
            {"apps": [0]},
            {"apps": []},
            {"apps": [2, 5]},
            {"apps": [1, 2**32 - 1]},
        ]

        bytes_written = pb.deviceapps_xwrite_pb(messages, TEST_FILE)

        self.assertTrue(bytes_written > 0)
        self.assertTrue(os.path.isfile(TEST_FILE))

        unpacked = list(pb.deviceapps_xread_pb(TEST_FILE))

        self.assertEqual(len(unpacked), len(messages))
        for m1, m2 in zip(expected, unpacked):
            self.assertMessagesEqual(m1, m2)
