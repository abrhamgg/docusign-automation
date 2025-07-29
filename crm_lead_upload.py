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
# Utility Functions
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
    # Parse and validate input mappings
    try:
        map_data_dict = json.loads(map_data)
        map_data = NameMap(**map_data_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid map_data: {str(e)}")

    # Parse custom fields list
    try:
        customeFields = json.loads(customeFields)
        customeFields = [field.strip() for field in customeFields if field.strip()]
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for customFields")

    email_phone_contact_id_map = {}

    members_df = pd.read_csv(members_file.file, index_col=False)
    leads_df = pd.read_csv(new_members_file.file, index_col=False)

    def normalize_phone(phone: str) -> str:
        """
        Normalizes phone number to XXX-XXX-XXXX format.
        Returns an empty string if the phone number cannot be formatted this way.
        """
        if pd.isna(phone) or not isinstance(phone, str):
            return ""

        phone = phone.strip()
        if not phone:
            return ""

        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)

        # If it's an 11-digit number starting with '1', remove the '1'
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]

        # Format if it's exactly 10 digits
        if len(digits) == 10:
            return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
        else:
            return ""


    # Build map of email/phone to contact ID for fast lookup
    for _, row in members_df.iterrows():
        email = row.get("Email")
        phone = normalize_phone(row.get("Phone"))
        contact_id = row.get("Contact Id")

        if pd.notna(email):
            email_phone_contact_id_map[email] = contact_id
        if pd.notna(phone):
            email_phone_contact_id_map[phone] = contact_id

    # Get all available custom fields from CRM
    result = await get_custom_fields(locationId, access_token)
    custom_fields = result.get("customFields", [])
    if not custom_fields:
        raise HTTPException(status_code=400, detail="No custom fields available")

    # Build name-to-ID map for custom fields
    custom_field_id_map = {field['name'].strip(): field["id"] for field in custom_fields}

    general_property_fields = {
        "Property Address": "PropertyAddress",
        "Property City": "PropertyCity",
        "Property State": "PropertyState",
        "Property Zip": "PropertyZip"
    }

    # Main tracking object
    result_data = {
        'new_leads': 0,
        'existing_leads': 0,
        'error': 0,
        'total_': 0,
        'skipped_rows': [],
    }

    # ✅ Main loop: iterate through new leads
    for _, row in leads_df.iterrows():
        result_data['total_'] += 1
        row = row.where(pd.notna(row), None)

        email = row.get(map_data.email)
        phone = normalize_phone(row.get(map_data.phone))

        # ✅ Skip leads missing both email and phone, and log the reason
        if not email and not phone:
            result_data["error"] += 1
            result_data["skipped_rows"].append({
                "reason": "Missing both email and phone",
                "row_data": row.to_dict()
            })
            continue

        try:
            # Prepare custom field payload
            custom_field_values = [
                {"id": custom_field_id_map[field], "value": row.get(field, "")}
                for field in customeFields if field in custom_field_id_map
            ]

            contact_id = email_phone_contact_id_map.get(email) or email_phone_contact_id_map.get(phone)

            if not contact_id:
                # Create new contact
                phone_clean = normalize_phone(row.get(map_data.phone)) if row.get(map_data.phone) else ""
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
                    "phone": phone_clean,
                    "country": row.get(map_data.Country),
                    "locationId": locationId,
                    "customFields": new_custom_fields,
                    "tags": [tag.strip() for tag in row.get(map_data.Tag).split(",")] if pd.notna(row.get(map_data.Tag)) else []
                }

                response = create_contact(contact_payload, access_token)
                print("Create contact response:", response)

                # ✅ If contact creation failed, track and skip
                if response.get("statusCode", 200) >= 400:
                    result_data["error"] += 1
                    result_data["skipped_rows"].append({
                        "reason": f"API error on contact creation (status: {response.get('statusCode')})",
                        "row_data": row.to_dict()
                    })
                    continue

                result_data["new_leads"] += 1
                contact_id = response.get("contactId")
                if email:
                    email_phone_contact_id_map[email] = contact_id
                if phone:
                    email_phone_contact_id_map[phone] = contact_id

            else:
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

                # ✅ Log update errors
                if response.get("error"):
                    result_data["error"] += 1
                    result_data["skipped_rows"].append({
                        "reason": "API error on update",
                        "row_data": row.to_dict()
                    })
                    continue

                result_data["existing_leads"] += 1

        except Exception as e:
            # ✅ Catch and log unexpected errors for each row
            result_data["error"] += 1
            result_data["skipped_rows"].append({
                "reason": f"Unhandled exception: {str(e)}",
                "row_data": row.to_dict()
            })
            continue


    # ✅ Final summary includes skipped rows with reasons
    return result_data
