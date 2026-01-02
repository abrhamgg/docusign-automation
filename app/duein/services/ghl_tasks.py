import httpx
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


async def create_task(
    contact_id: str,
    title: str,
    body: str,
    assigned_to: Optional[str] = None,
    due_date_iso: Optional[str] = None,
) -> dict:
    if not settings.GHL_API_TOKEN:
        raise RuntimeError("GHL API token is not configured in environment")

    url = f"{settings.GHL_BASE_URL}/contacts/{contact_id}/tasks"
    headers = {
        "Authorization": f"Bearer {settings.GHL_API_TOKEN}",
        "Version": settings.GHL_API_VERSION,
        "Content-Type": "application/json",
    }

    payload = {
        "title": title,
        "body": body,
        "completed": False,
    }
    if due_date_iso:
        payload["dueDate"] = due_date_iso
    if assigned_to:
        payload["assignedTo"] = assigned_to

    logger.debug("Sending task to GHL for contact=%s assignedTo=%s", contact_id, assigned_to)

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("GHL API request failed: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"GHL API returned {resp.status_code}: {resp.text}") from exc

    try:
        data = resp.json()
        try:
            logger.info("GHL created task: id=%s title=%s dueDate=%s contact=%s", data.get("id"), data.get("title"), data.get("dueDate"), data.get("contactId") or data.get("contact") )
        except Exception:
            logger.debug("GHL response (non-json fields): %s", data)
        return data
    except Exception:
        return {"status_code": resp.status_code, "text": resp.text}