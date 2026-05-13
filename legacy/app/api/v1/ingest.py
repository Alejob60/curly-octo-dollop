from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.core.db_clients import mongo_db
from app.workers.dispatcher import historical_dispatcher

router = APIRouter()


@router.get("/status")
async def get_ingest_status():
    now = datetime.now(timezone.utc)
    minute_ago = now - timedelta(minutes=1)

    total_processed = await mongo_db.pqrsd_history.count_documents({})
    processed_last_minute = await mongo_db.pqrsd_history.count_documents(
        {"updated_at": {"$gte": minute_ago.isoformat()}}
    )
    queue_pending = await mongo_db.ingestion_queue.count_documents({"status": "pending"})
    queue_failed = await mongo_db.ingestion_queue.count_documents({"status": "failed"})

    last_record = await mongo_db.pqrsd_history.find_one(
        {},
        projection={"_id": 0, "updated_at": 1, "radicado": 1},
        sort=[("updated_at", -1)],
    )

    pubsub_state = await historical_dispatcher.get_dispatcher_health()

    return {
        "status": "ok",
        "processed_total": total_processed,
        "processed_per_minute": processed_last_minute,
        "queue": {
            "pending": queue_pending,
            "failed": queue_failed,
        },
        "last_processed_record": last_record,
        "pubsub": pubsub_state,
        "generated_at": now.isoformat(),
    }
