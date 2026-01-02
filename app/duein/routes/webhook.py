"""Permissive webhook route to handle GHL custom webhooks (copied from dueIn).

This file is namespaced under `app.duein` to avoid conflicts with existing
modules in the docusign-automation project.
"""
from typing import Any, Dict, Optional
import logging
import re
from fastapi import APIRouter, Body, HTTPException
from fastapi import status as http_status

from app.core.config import settings
from app.duein.services.ghl_tasks import create_task as ghl_create_task
from app.duein.utils.time import calculate_due_date_utc
from app.duein.utils.rules import resolve_follow_up_days

logger = logging.getLogger(__name__)
router = APIRouter()


def _safe_get_contact_id(payload: Dict[str, Any]) -> Optional[str]:
    candidates = [
        payload.get("contact_id"),
        payload.get("contactId"),
        payload.get("id"),
        payload.get("contact", {}).get("id") if isinstance(payload.get("contact"), dict) else None,
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
    return None


def _extract_follow_up_status(payload: Dict[str, Any]) -> Optional[str]:
    custom_data = payload.get("customData") or payload.get("custom_data") or {}
    if isinstance(custom_data, dict):
        for key in ("Follow up Status", "Follow Up Status", "follow up status"):
            v = custom_data.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()

    keys = ["Follow up status", "Follow Up Status", "follow_up_status", "followUpStatus", "follow up status"]
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else None
    if contact and isinstance(contact.get("customFields"), dict):
        for val in contact.get("customFields").values():
            if isinstance(val, str) and "follow up" in val.lower():
                return val.strip()

    if isinstance(payload.get("customFields"), dict):
        for val in payload.get("customFields").values():
            if isinstance(val, str) and "follow up" in val.lower():
                return val.strip()

    return None


def _extract_assigned_to(payload: Dict[str, Any]) -> Optional[str]:
    candidates = []
    try:
        cd = payload.get("customData") or {}
        candidates.append(cd.get("assigned_to"))
    except Exception:
        pass
    candidates.extend([
        payload.get("assigned_to"),
        payload.get("owner_id"),
        payload.get("ownerId"),
    ])
    contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else None
    if contact:
        candidates.extend([contact.get("assignedTo"), contact.get("assigned_to"), contact.get("owner_id"), contact.get("ownerId")])

    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
    return None


def _extract_location_id(payload: Dict[str, Any]) -> Optional[str]:
    loc = payload.get("location")
    if isinstance(loc, dict):
        idv = loc.get("id") or loc.get("location_id") or loc.get("locationId")
        if isinstance(idv, str) and idv.strip():
            return idv.strip()

    for k in ("locationId", "location_id"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _parse_follow_label(label: Optional[str]) -> (Optional[str], int):
    if not label or not isinstance(label, str):
        return None, 1

    s = label.strip()
    freq = None
    if re.search(r"\bdaily\b", s, re.I):
        freq = "Daily"
    elif re.search(r"\bweekly\b", s, re.I):
        freq = "Weekly"
    elif re.search(r"\bmonthly\b", s, re.I):
        freq = "Monthly"
    else:
        m = re.search(r"follow\s*up\s*(daily|weekly|monthly)", s, re.I)
        if m:
            freq = m.group(1).capitalize()

    num_match = re.search(r"(\d+)", s)
    idx = int(num_match.group(1)) if num_match else 1
    return freq, idx


@router.post("/webhook/create-task")
async def create_task(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    contact_id = _safe_get_contact_id(payload)
    if not contact_id:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="missing contact_id")

    follow_status = _extract_follow_up_status(payload)
    assigned_to = _extract_assigned_to(payload)
    location_id = _extract_location_id(payload)

    freq, idx = _parse_follow_label(follow_status)
    title = f"Follow Up {freq}" if freq else "Follow Up"
    body_text = f"{freq} Follow Up #{idx}" if freq else f"Follow Up #{idx}"

    due_date_iso = None
    try:
        if follow_status:
            days = resolve_follow_up_days(follow_status)
            due_date_iso = calculate_due_date_utc(days)
        else:
            due_date_iso = calculate_due_date_utc(0)
    except Exception:
        due_date_iso = calculate_due_date_utc(0)

    outgoing = {"title": title, "body": body_text, "completed": False, "dueDate": due_date_iso}
    if assigned_to:
        outgoing["assignedTo"] = assigned_to

    if payload.get("dry_run") is True or payload.get("dryRun") is True:
        return {
            "status": "dry-run",
            "contact_id": contact_id,
            "location_id": location_id,
            "extracted_follow_status": follow_status,
            "outgoing": outgoing,
        }

    try:
        resp = await ghl_create_task(contact_id=contact_id, title=title, body=body_text, assigned_to=assigned_to, due_date_iso=due_date_iso)
    except Exception as exc:
        logger.exception("Failed to create task for contact=%s", contact_id)
        raise HTTPException(status_code=http_status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return {"status": "success", "contact_id": contact_id, "ghl_response": resp}
