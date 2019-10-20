# Building a Python C Extension Module
The task is to build C extension module for serializing and deserializing
protobuf messages.

## **Requirements**
* C compiler (`gcc` or `clang`)
* Python 3.6+
* Python setuptools package (`python3-setuptools` for Debian / Ubuntu)
* Header files and a static library for Python 3 (`python3-dev` for Debian / Ubuntu)
* Protocol Buffers C compiler (`protobuf-c-compiler` for Debian / Ubuntu)
* Protocol Buffers C static library and headers (`libprotobuf-c-dev` for Debian / Ubuntu)
* Zlib header files (`zlib1g-dev` for Debian / Ubuntu)

## **Installation**
```
git clone https://github.com/stkrizh/otus.git
cd otus/protobuf_serializer
protoc-c --c_out=. deviceapps.proto
python3 setup.py test install
```

## **To run with Docker**
```
cd otus/protobuf_serializer
docker build -t pb .
```
To run container:
```
docker run -it --rm pb
```

## **Example**
```python
import pb

messages = [
    {
        "device": {
            "type": "idfa", 
            "id": "e7e1a50c0ec2747ca56cd9e1558c0d7c"
        },
        "lat": 67.7835424444,
        "lon": -22.8044005471, 
        "apps": [1, 2, 3, 4]
    },
    {
        "device": {
            "type": "gaid", 
            "id": "foobar"
        },
        "lat": 37.023411242,
        "lon": 22.8044005471,
        "apps": []
    },
]

# Write
bytes_written = pb.deviceapps_xwrite_pb(messages, "test.pb.gz")
assert bytes_written > 0

# Read
unpacked = list(pb.deviceapps_xread_pb("test.pb.gz"))
assert unpacked == messages

```
