#!/bin/sh
set -xe

yum install -y  gcc \
				make \
				protobuf \
				protobuf-c \
				protobuf-c-compiler \
				protobuf-c-devel \
                python36 \
				python36-devel \
				python36-setuptools \
				gdb 

ulimit -c unlimited
cd /tmp/otus/
protoc-c --c_out=. deviceapps.proto
python3 setup.py test
