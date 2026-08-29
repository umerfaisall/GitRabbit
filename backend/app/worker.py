import redis.exceptions

from app.services.redis_client import redis_client
from app.models.webhook import PrEvent


QUEUE_NAME = "pr-review-jobs"

def worker():
    while True:
        try:
            result = redis_client.brpop(QUEUE_NAME, timeout=5)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            continue
        if result is None:
            continue
        _, raw = result
        data = PrEvent.model_validate_json(raw)
        print(data)

if __name__ == "__main__":
    worker()