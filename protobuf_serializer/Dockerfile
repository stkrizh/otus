FROM debian:stable-slim

RUN apt-get update \
    && apt-get install -y \
        gcc protobuf-c-compiler libprotobuf-c-dev zlib1g-dev \
        python3 python3-dev python3-pip python3-setuptools

WORKDIR /app
COPY . .

RUN protoc-c --c_out=. deviceapps.proto
RUN python3 setup.py test

CMD ["python3"]
