from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import hashlib
import hmac
from app.config import get_settings
from app.models.webhook import PrEvent
from app.services.redis_client import redis_client

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

settings = get_settings()
RELEVENT_ACTIONS = {"opened", "synchronize"}
QUEUE_NAME = "pr-review-jobs"   


@router.post("/github")
async def handle_github_webhook(request: Request):
    
    rawData = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature header")

    expected_signature = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        rawData,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    eventType = request.headers.get("X-GitHub-Event")
    parsedData = await request.json()

    if eventType != "pull_request" or parsedData.get("action") not in RELEVENT_ACTIONS:
        return {"status": "ignored"}

    event = PrEvent.from_payload(parsedData)

    redis_client.lpush(
        QUEUE_NAME,
        event.model_dump_json()
    )

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "pr_id": event.pr_id, "commit_sha": event.commit_sha},
    )