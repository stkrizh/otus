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
Document Length:        11 bytes

Concurrency Level:      100
Time taken for tests:   136.478 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      8250000 bytes
HTML transferred:       550000 bytes
Requests per second:    366.36 [#/sec] (mean)
Time per request:       272.955 [ms] (mean)
Time per request:       2.730 [ms] (mean, across all concurrent requests)
Transfer rate:          59.03 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.5      0      14
Processing:     5  272  19.6    272     557
Waiting:        4  271  19.6    271     555
Total:          5  273  19.7    273     557

Percentage of the requests served within a certain time (ms)
  50%    273
  66%    278
  75%    281
  80%    283
  90%    288
  95%    294
  98%    300
  99%    306
 100%    557 (longest request)
```
