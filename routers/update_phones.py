from fastapi import APIRouter
from pydantic import BaseModel
from services.token_service import get_valid_token
import requests

router = APIRouter()

# ✅ Pydantic model
class PhoneInfo(BaseModel):
    phone: str
    type: str

class UpdatePhoneRequest(BaseModel):
    contact_id: str
    location_id: str
    phones: list[dict]  # allow raw dicts so we can sanitize ourselves


# 🏷️ Clean up phone type labels
def get_label_from_type(phone_type: str):
    pt = phone_type.lower().strip()
    if pt in ["mobile", "mobile or cell", "wireless"]:
        return "Mobile"
    elif pt == "home":
        return "Home"
    elif pt == "work":
        return "Work"
    elif pt in ["landline", "voip"]:
        return "Landline"
    return "Other"


@router.post("/update-phones")
def update_phones(payload: UpdatePhoneRequest):
    token = get_valid_token(payload.location_id)

    print(f"🔗 Using token for location {payload}")
    # ✅ Sanitize and validate phones
    cleaned_phones = []
    for phone_obj in payload.phones:
        # Ensure it's a dict and has correct keys
        if isinstance(phone_obj, dict) and "phone" in phone_obj and "type" in phone_obj:
            phone_val = str(phone_obj["phone"]).strip()
            type_val = str(phone_obj["type"]).strip()
            if phone_val and type_val:
                cleaned_phones.append({"phone": phone_val, "type": type_val})
            else:
                print(f"❌ Skipping phone (missing value): {phone_obj}")
        else:
            print(f"❌ Skipping malformed phone: {phone_obj}")

    if not cleaned_phones:
        return {"error": "No valid phone numbers to process."}

    # ✅ Prepare payload
    update_data = {
        "phone": cleaned_phones[0]["phone"],
        "phoneLabel": get_label_from_type(cleaned_phones[0]["type"]),
        "additionalPhones": [
            {
                "phone": phone["phone"],
                "phoneLabel": get_label_from_type(phone["type"])
            }
            for phone in cleaned_phones[1:]
        ]
    }

    # 🔁 Send PUT request to GHL
    url = f"https://services.leadconnectorhq.com/contacts/{payload.contact_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }

    resp = requests.put(url, headers=headers, json=update_data)

    return {
        "status": resp.status_code,
        "payload_sent": update_data,
        "ghl_response": resp.json()
    }
