# Simple HTTP server
The server uses multiple threads to handle requests. Number of threads is optional (4 by default).
The server supports only GET / HEAD requests and serves static files in specified document root.

## **Requirements**
* Python 3.6+

## **Installation**
```
git clone https://github.com/stkrizh/otus.git
cd otus
```

## **Tests**
```
python3.6 -m httpserver.tests
```

## **To run HTTP-server**
```
python3.6 -m httpserver --root /path/to/document/root --port 8080 --workers 10
```

## **ApacheBench (ab) test for 100 workers**
```
ab -n 50000 -c 100 -r http://localhost:80/
This is ApacheBench, Version 2.3 <$Revision: 1807734 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        Fancy-Python-HTTP-Server
Server Hostname:        localhost
Server Port:            80

Document Path:          /
Document Length:        13 bytes

Concurrency Level:      100
Time taken for tests:   111.518 seconds
Complete requests:      50000
Failed requests:        0
Non-2xx responses:      50000
Total transferred:      8750000 bytes
HTML transferred:       650000 bytes
Requests per second:    448.36 [#/sec] (mean)
Time per request:       223.035 [ms] (mean)
Time per request:       2.230 [ms] (mean, across all concurrent requests)
Transfer rate:          76.62 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    1  26.3      0    1031
Processing:     1  222  18.6    222     621
Waiting:        1  221  18.5    221     620
Total:          1  223  33.7    222    1480

Percentage of the requests served within a certain time (ms)
  50%    222
  66%    227
  75%    229
  80%    231
  90%    236
  95%    240
  98%    246
  99%    250
 100%   1480 (longest request)
```
