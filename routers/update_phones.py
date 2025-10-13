from fastapi import APIRouter, Request
from services.token_service import get_valid_token
import requests

router = APIRouter()

def get_label_from_type(phone_type: str) -> str:
    pt = phone_type.lower().strip()
    if pt in ["mobile", "wireless", "cell"]:
        return "Mobile"
    elif pt == "home":
        return "Home"
    elif pt == "work":
        return "Work"
    elif pt in ["landline", "voip"]:
        return "Landline"
    return "Mobile"  # fallback default

# ✅ Reusable function (can be imported anywhere)
def update_phones_in_ghl(contact_id: str, location_id: str, phones: list):
    try:
        if not contact_id or not location_id:
            return {"error": "Missing contact_id or location_id"}

        if not phones:
            return {"error": "No valid phone numbers provided."}

        # 🔐 Get token (replace later with your token fetch logic)
        token = get_valid_token(location_id)
        return
       # 📥 Fetch existing contact data
        existing_resp = requests.get(
            f"https://services.leadconnectorhq.com/contacts/{contact_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Version": "2021-07-28"
            }
        )
        existing = existing_resp.json()

        existing_phones = []

        # Include main phone if it exists
        if existing.get("phone"):
            existing_phones.append({
                "phone": existing["phone"],
                "type": existing.get("phoneLabel", "Mobile")
            })

        # Include additionalPhones
        for p in existing.get("additionalPhones", []):
            if "phone" in p:
                existing_phones.append({
                    "phone": p["phone"],
                    "type": p.get("phoneLabel", "Mobile")
                })

        # ✨ Merge + Deduplicate
        seen = set()
        all_phones = existing_phones + phones
        merged_phones = []
        for p in all_phones:
            number = p["phone"].strip()
            norm = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if norm and norm not in seen:
                seen.add(norm)
                merged_phones.append({
                    "phone": number,
                    "phoneLabel": get_label_from_type(p.get("type", "Mobile"))
                })

        if not merged_phones:
            return {"error": "All phone numbers are duplicates or empty."}

        update_data = {
            "phone": merged_phones[0]["phone"],
            "phoneLabel": merged_phones[0]["phoneLabel"],
            "additionalPhones": merged_phones[1:]
        }

        # ✅ Update contact
        resp = requests.put(
            f"https://services.leadconnectorhq.com/contacts/{contact_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            },
            json=update_data
        )

        return {
            "status": resp.status_code,
            "payload_sent": update_data,
            "ghl_response": resp.json()
        }

    except Exception as e:
        return {"error": str(e)}

# 🚀 FastAPI route — just calls the helper
@router.post("/update-phones")
async def update_phones(request: Request):
    try:
        body = await request.json()

        # Handle if data is wrapped in `customData`
        raw_data = body.get("customData", body)

        # Normalize keys (fix trailing space issues)
        data = {k.strip().lower(): v for k, v in raw_data.items()}

        contact_id = data.get("contact_id")
        location_id = data.get("location_id")

        if not contact_id or not location_id:
            return {"error": "Missing contact_id or location_id"}

        # 🔍 Extract new phones
        phones = []
        for i in range(1, 21):
            phone_key = f"phone {i}"
            type_key = f"phone {i} type"
            phone = data.get(phone_key, "").strip()
            phone_type = data.get(type_key, "Mobile").strip()
            if phone:
                phones.append({
                    "phone": phone,
                    "type": phone_type
                })

        if not phones:
            return {"error": "No valid phone numbers provided."}

        # 🔐 Get token
        token = get_valid_token(location_id)

        # 📥 Fetch existing phones from GHL
        existing_resp = requests.get(
            f"https://services.leadconnectorhq.com/contacts/{contact_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Version": "2021-07-28"
            }
        )
        existing = existing_resp.json()

        existing_phones = []

        # Include main phone if it exists
        if "phone" in existing and existing["phone"]:
            existing_phones.append({
                "phone": existing["phone"],
                "type": existing.get("phoneLabel", "Mobile")
            })

        # Include additionalPhones
        for p in existing.get("additionalPhones", []):
            if "phone" in p:
                existing_phones.append({
                    "phone": p["phone"],
                    "type": p.get("phoneLabel", "Mobile")
                })

        # ✨ Merge and deduplicate
        seen = set()
        all_phones = existing_phones + phones
        merged_phones = []
        for p in all_phones:
            number = p["phone"].strip()
            norm_number = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if norm_number and norm_number not in seen:
                seen.add(norm_number)
                merged_phones.append({
                    "phone": number,
                    "phoneLabel": get_label_from_type(p.get("type", "Mobile"))
                })

        if not merged_phones:
            return {"error": "All phone numbers are duplicates or empty."}

        update_data = {
            "phone": merged_phones[0]["phone"],
            "phoneLabel": merged_phones[0]["phoneLabel"],
            "additionalPhones": merged_phones[1:]
        }

        # ✅ PUT update
        resp = requests.put(
            f"https://services.leadconnectorhq.com/contacts/{contact_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            },
            json=update_data
        )

        return {
            "status": resp.status_code,
            "payload_sent": update_data,
            "ghl_response": resp.json()
        }

    except Exception as e:
        return {"error": str(e)}