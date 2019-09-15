from scoring import settings

settings.REDIS_DB = settings.REDIS_TESTING_DB
settings.RETRY_DELAY = 0.1
settings.RETRY_N_TIMES = 2
settings.REDIS_CONNECTION_TIMEOUT = 1
