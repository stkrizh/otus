# MemcLoad
The intent of this program is to use Python's multiprocessing module for parsing 
log files (see `sample.tsv.gz`) and caching parsed lines to Memcached.

## **Requirements**
* Python 3.6
  - python-memcached
  - protobuf
* Memcached

## **Installation**
```
git clone https://github.com/stkrizh/otus.git
cd otus
pip install -r memcload/requirements.txt
```

## **Tests**
```
python -m memcload.test
```

## **Examples**
To get help:
```
python -m memcload --help
```

Dry run:
```
python -m memcload --dry --pattern="./memcload/*.tsv.gz"
```

Make sure that Memcached is running:
```
python -m memcload --pattern="/path/to/logs/*.tsv.gz"
```
