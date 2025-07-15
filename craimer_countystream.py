# main.py
from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime, timezone
from models import TenantDataRecord
import httpx
from dotenv import load_dotenv
import re
import json

load_dotenv()

router = APIRouter(
    prefix="/craimer",
    tags=["Craimer County Stream"], 
)

WEBHOOK_URL = "https://services.leadconnectorhq.com/hooks/qsXePQTcTU21ZEUWJHq4/webhook-trigger/fa4b7258-b93c-4ff9-9365-07ab4e8bd222"

@router.post("/data-ingest")
async def ingest_data(request: Request):
    body = await request.json()

    tenant_id = body.pop("tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing tenant_id")

    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    # Save to DynamoDB as valid JSON
    try:
        TenantDataRecord.create_record(
            tenant_id=tenant_id,
            timestamp=timestamp,
            data=body
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB Error: {str(e)}")

    # Prepare webhook payload
    webhook_payload = {
        "tenant_id": tenant_id,
        "timestamp": timestamp,
        **body
    }

    # Flatten phones into top-level fields
    if "phones" in webhook_payload and isinstance(webhook_payload["phones"], list):
        for idx, phone_entry in enumerate(webhook_payload["phones"]):
            # Add the phone number itself
            webhook_payload[f"phone_{idx}"] = phone_entry.get("phone")
            # Optionally add other fields, e.g., type or verification
            webhook_payload[f"phone_{idx}_type"] = phone_entry.get("type")
            webhook_payload[f"phone_{idx}_verification_name"] = (
                phone_entry.get("verification", {}).get("name")
            )
            webhook_payload[f"phone_{idx}_verification_ownership"] = (
                phone_entry.get("verification", {}).get("ownership")
            )
            webhook_payload[f"phone_{idx}_metadata_target"] = (
                phone_entry.get("metadata", {}).get("target")
            )

        # Remove the original phones array if you don't want it
        del webhook_payload["phones"]

    # Send to webhook
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(WEBHOOK_URL, json=webhook_payload)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Webhook Error: {str(e)}")

    return {"status": "success", "message": "Data saved and forwarded."}