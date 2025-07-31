from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from urllib.parse import urlencode
import pandas as pd
import requests
import json
import re

router = APIRouter(prefix='/crm')

# -----------------------------
# Models
# -----------------------------

class NameMap(BaseModel):
    """
    Model for mapping CRM field names to input CSV headers.
    """
    firstName: str
    lastName: str
    email: str
    phone: str
    PropertyAddress: str
    PropertyCity: str
    PropertyState: str
    PropertyZip: str
    PropertyAddressMap: str
    Country: str
    fullName: str = None
    Tag: str = None


# -----------------------------
# Functions
# -----------------------------

def create_contact(data, access_token):
    url = "https://services.leadconnectorhq.com/contacts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()


def update_contact(data, access_token, contact_id):
    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }
    response = requests.put(url, headers=headers, json=data)
    return response.json()


async def get_custom_fields(location_id: str, access_token: str):
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token provided.")

    url = f"https://services.leadconnectorhq.com/locations/{location_id}/customFields"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching custom fields: {str(e)}")


# -----------------------------
# Main Endpoint
# -----------------------------

@router.post("/upload-contact")
async def create_contact_from_csv(
    locationId: str,
    access_token: str = Form(...),
    map_data: str = Form(...),
    members_file: UploadFile = File(...),
    new_members_file: UploadFile = File(...),
    customeFields: str = Form(...)
):
    
    try:
        map_data_dict = json.loads(map_data)
        map_data = NameMap(**map_data_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid map_data: {str(e)}")

    try:
        customeFields = json.loads(customeFields)
        customeFields = [field.strip() for field in customeFields if field.strip()]
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for customFields")

    email_phone_contact_id_map = {}

    members_df = pd.read_csv(members_file.file, index_col=False)
    leads_df = pd.read_csv(new_members_file.file, index_col=False)
    # Map emails/phones to contact IDs
    for _, row in members_df.iterrows():
        email = row.get("Email")
        phone = row.get("Phone")
        phone = re.sub(r'\D', '', str(phone)) if pd.notna(phone) else None
        contact_id = row.get("Contact Id")

        if pd.notna(email):
            email_phone_contact_id_map[email] = contact_id
        if pd.notna(phone):
            email_phone_contact_id_map[phone] = contact_id

    result = await get_custom_fields(locationId, access_token)
    if not result or "customFields" not in result:
        raise HTTPException(status_code=400, detail="Failed to fetch custom fields")
    custom_fields = result.get("customFields", [])
    if not custom_fields:
        raise HTTPException(status_code=400, detail="No custom fields available")

    custom_field_id_map = {field['name'].strip(): field["id"] for field in custom_fields}
    general_property_fields = {"Property Address": "PropertyAddress",
                               "Property City": "PropertyCity",
                               "Property State": "PropertyState",
                               "Property Zip": "PropertyZip"
                               }

    result_data = {
        'new_leads': 0,
        'existing_leads': 0,
        'error': 0,
        'total_': 0
    }

    for _, row in leads_df.iterrows():
        result_data['total_'] += 1

        # Clean NaNs
        row = row.where(pd.notna(row), None)

        email = row.get(map_data.email)
        phone = row.get(map_data.phone)

        if not email and not phone:
            result_data["error"] += 1
            continue
        if phone:
            phone =re.sub(r'\D', '', str(phone))
            if len(phone) <= 10:
                phone = "1" + phone  # Assuming US format, prepend '1' if phone is less than 10 digits
        # Prepare custom fields
        custom_field_values = [
            {"id": custom_field_id_map[field], "value": row.get(field, "")}
            for field in customeFields if field in custom_field_id_map
            
        ]
        contact_id = email_phone_contact_id_map.get(email) or email_phone_contact_id_map.get(phone) or None
        if not contact_id:
            try:
                # if not phone:
                #     raise ValueError("Phone number is invalid or empty.")
                new_custom_fields = []
                for key, attr in general_property_fields.items():
                    val = row.get(getattr(map_data, attr))
                    if pd.notna(val) and key in custom_field_id_map:
                        new_custom_fields.append({
                            "id": custom_field_id_map[key],
                            "value": val
                        })
                        
                new_custom_fields.extend(custom_field_values)

                contact_payload = {
                    "firstName": row.get(map_data.firstName),
                    "lastName": row.get(map_data.lastName),
                    "fullName": row.get(map_data.fullName) if pd.notna(row.get(map_data.fullName)) else None,
                    "email": email,
                    "phone": phone,
                    "country": row.get(map_data.Country),
                    "locationId": locationId,
                    "customFields": new_custom_fields,
                    "tags": [tag.strip() for tag in row.get(map_data.Tag).split(",")] if pd.notna(row.get(map_data.Tag)) else []
                }


                response = create_contact(contact_payload, access_token)
                if response.get("statusCode", 200) >= 400:
                    result_data["error"] += 1
                    continue

                result_data["new_leads"] += 1
                contact_id = response.get("contactId")
                if email:
                    email_phone_contact_id_map[email] = contact_id
                if phone:
                    email_phone_contact_id_map[phone] = contact_id

            except Exception as e:
                result_data["error"] += 1
            continue
        # Update existing contact
        member_data = members_df[members_df["Contact Id"] == contact_id]
        populated_fields = []

        for i in range(2, 6):
            col = f"Property Address {i}"
            if col not in member_data or pd.isna(member_data[col].iloc[0]) or member_data[col].iloc[0] == "":
                city = row.get(getattr(map_data, "PropertyCity")) or ""
                state = row.get(getattr(map_data, "PropertyState")) or ""
                zip_code = row.get(getattr(map_data, "PropertyZip")) or ""
                address = f"{row.get(getattr(map_data, general_property_fields['Property Address']))}, {city}, {zip_code}, {state}"

                map_key = f"Property Address {i}"
                if pd.notna(address) and map_key in custom_field_id_map:
                    populated_fields.append({
                        "id": custom_field_id_map[map_key],
                        "value": address
                    })
                break

        populated_fields.extend(custom_field_values)
        update_data = {"customFields": populated_fields}

        response = update_contact(update_data, access_token, contact_id)
        if response.get("error"):
            result_data["error"] += 1
            continue
        result_data["existing_leads"] += 1

    return result_data
