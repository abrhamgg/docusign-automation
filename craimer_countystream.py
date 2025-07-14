# main.py
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from models import TenantDataRecord
import httpx
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/craimer",
    tags=["Craimer County Stream"], 
)

WEBHOOK_URL = "https://webhook.site/38153e82-a0d5-4485-8b97-392fdea3333f"

class IngestRequest(BaseModel):
    tenant_id: str
    data: dict


@router.post("/data-ingest")
async def ingest_data(payload: IngestRequest):
    # Generate timestamp
    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    try:
        # Save to DynamoDB
        TenantDataRecord.create_record(
            tenant_id=payload.tenant_id,
            timestamp=timestamp,
            data=payload.data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB Error: {str(e)}")

    # Forward to webhook
    webhook_payload = {
        "tenant_id": payload.tenant_id,
        "timestamp": timestamp,
        **payload.data
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(WEBHOOK_URL, json=webhook_payload)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Webhook Error: {str(e)}")

    return {"status": "success", "message": "Data saved and forwarded."}
