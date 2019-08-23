# Scoring API
Otus Scoring API task

## **Requirements**
* Python 2.7
  - mock
  - redis
  - requests
* Redis-server

## **Installation**
```
git clone https://github.com/stkrizh/otus.git
cd otus
pip install -r scoring/requirements.txt
```

## **Default settings**
```
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PASSWORD = None
REDIS_DB = 0
REDIS_TESTING_DB = 1
REDIS_CONNECTION_TIMEOUT = 5

RETRY_N_TIMES = 5
RETRY_DELAY = 1
```

## **Tests**
```
python -m scoring.tests.unit
python -m scoring.tests.functional
python -m scoring.tests.integration
```

To run all tests:
```
python -m scoring.tests
```

## **To run HTTP-server**
```
python -m scoring.api
```

## **Example requests**
```
curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", "arguments": {"phone": "79991234567", "email": "test@email.ru"}}' http://127.0.0.1:8080/method/
```
Response:
```
{"code": 200, "response": {"score": 3.0}}
```
<br>

```
curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "token":"55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", "arguments": {"client_ids": [1,2,3,4], "date": "30.07.2017"}}' http://127.0.0.1:8080/method/
```
Response:
```
{"code": 200, "response": {"1": ["music", "cinema"], "3": ["music", "geek"], "2": ["books", "tv"], "4": ["travel", "pets"]}}
````
