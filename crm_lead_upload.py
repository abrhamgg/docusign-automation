from fastapi import APIRouter, HTTPException, UploadFile, File, Form,Request

from pydantic import BaseModel,Field,HttpUrl
import pandas as pd
import requests
import json
import re
from typing import List, Optional
import os
import requests
from services.token_service import get_valid_token
from routers.update_phones import update_phones_in_ghl
from fastapi import status, HTTPException
import logging
logger = logging.getLogger(__name__)
import json
AUTH_URL = os.getenv("AUTH_URL")

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

class Phone(BaseModel):
    number: str = Field(..., alias="phone")
    type: str
    verification_name: str
    verification_ownership: int
    metadata_target: str

# Define the main request body


# -----------------------------
# Utility Functions
# -----------------------------


def extract_message_from_error(error):
    # If error is a string and contains JSON, extract the JSON part
    if isinstance(error, str):
        import re
        match = re.search(r'({.*})', error)
        if match:
            try:
                error_json = json.loads(match.group(1))
                return error_json.get("message", error)
            except Exception:
                pass
        # If no JSON, return the string itself
        return error
    # If error is a dict
    if isinstance(error, dict):
        return error.get("message", str(error))
    return str(error)

def check_duplicates(token: str, location_id: str, email: str = None, phone: str = None) -> dict | None:
    if not token:
        raise HTTPException(status_code=400, detail="No access token provided.")

    url = "https://services.leadconnectorhq.com/contacts/search/duplicate"
    params = {
        "locationId": location_id,
        "email": email,
        "number": phone
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Version": "2021-07-28"
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json().get("contact")
        elif response.status_code == 404:
            # 404 means no duplicate found — return None
            return None
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"GHL Check Duplicate Error: {response.text}"
            )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error checking duplicates: {str(e)}"
        )
    
def create_contact(data, access_token):
    url = "https://services.leadconnectorhq.com/contacts"
    headers = {"Authorization": f"Bearer {access_token}", "Version": "2021-07-28"}
    return requests.post(url, headers=headers, json=data).json()

def update_contact(data, access_token, contact_id):
    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {"Authorization": f"Bearer {access_token}", "Version": "2021-07-28"}
    return requests.put(url, headers=headers, json=data).json()

def update_contacts(token: str, contact_id: str, contact_data: dict) -> tuple[dict | None, str | None]:
    if not token:
        raise HTTPException(status_code=400, detail="No access token provided.")
    
    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json"
    }

    try:
        response = requests.put(url, json=contact_data, headers=headers)
        if response.status_code == 200:
            return response.json(), None
        else:
            error_msg = f"Update failed: {response.status_code} - {response.text}"
            raise HTTPException(status_code=response.status_code, detail=error_msg)
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error updating contact: {str(e)}")
async def get_custom_fields(location_id: str, access_token: str):
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token provided.")
    url = f"https://services.leadconnectorhq.com/locations/{location_id}/customFields"
    headers = {"Authorization": f"Bearer {access_token}", "Version": "2021-07-28"}
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching custom fields: {str(e)}")

def normalize_phone(phone: str) -> str:
    if pd.isna(phone) or not isinstance(phone, str):
        return ""
    phone = phone.strip()
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    if len(digits) == 10:
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
    return ""
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
    # Parse mappings
    try:
        map_data = NameMap(**json.loads(map_data))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid map_data: {str(e)}")

    # Parse custom fields
    try:
        customeFields = [f.strip() for f in json.loads(customeFields) if f.strip()]
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for customFields")

    members_df = pd.read_csv(members_file.file, index_col=False)
    leads_df = pd.read_csv(new_members_file.file, index_col=False)

    # Build maps for email/phone -> contact ID
    email_to_id, phone_to_id = {}, {}
    for _, row in members_df.iterrows():
        email_val = row.get("Email")
        phone_val = normalize_phone(row.get("Phone"))
        contact_id = row.get("Contact Id")
        if pd.notna(email_val) and email_val:
            email_to_id[email_val.strip().lower()] = contact_id
        if pd.notna(phone_val) and phone_val:
            phone_to_id[phone_val] = contact_id

    # Fetch custom fields
    result = await get_custom_fields(locationId, access_token)
    custom_fields = result.get("customFields", [])
    custom_field_id_map = {f['name'].strip(): f["id"] for f in custom_fields}

    general_property_fields = {
        "Property Address": "PropertyAddress",
        "Property City": "PropertyCity",
        "Property State": "PropertyState",
        "Property Zip": "PropertyZip",
        "Property Address Map": "PropertyAddressMap"
    }

    # Tracking
    result_data = {
        'new_leads': 0,
        'existing_leads': 0,
        'error': 0,
        'total_': 0,
        'skipped_rows': [],
        'details': []
    }

    # Main loop
    for idx, row in leads_df.iterrows():
        result_data['total_'] += 1
        row = row.where(pd.notna(row), None)

        email = row.get(map_data.email)
        phone = normalize_phone(row.get(map_data.phone))
        email_key = email.strip().lower() if email else None
        phone_key = phone if phone else None

        normalized_data = row.to_dict()

        # Skip rows with no phone and no email
        if not email and not phone:
            result_data["error"] += 1
            result_data["skipped_rows"].append({
                "row_index": idx,
                "reason": "Missing both email and phone",
                "row_data": normalized_data
            })
            continue

        try:
            # Prepare custom fields
            custom_field_values = [
                {"id": custom_field_id_map[field], "value": row.get(field, "")}
                for field in customeFields if field in custom_field_id_map
            ]

            # Match existing contact
            contact_id = email_to_id.get(email_key) if email_key else None
            if not contact_id and phone_key:
                contact_id = phone_to_id.get(phone_key)

            if not contact_id:
                # Create new contact
                new_custom_fields = []
                for key, attr in general_property_fields.items():
                    val = row.get(getattr(map_data, attr))
                    if pd.notna(val) and key in custom_field_id_map:
                        new_custom_fields.append({"id": custom_field_id_map[key], "value": val})
                new_custom_fields.extend(custom_field_values)

                contact_payload = {
                    "firstName": row.get(map_data.firstName),
                    "lastName": row.get(map_data.lastName),
                    "fullName": row.get(map_data.fullName),
                    "email": email,
                    "phone": phone,
                    "country": row.get(map_data.Country),
                    "locationId": locationId,
                    "customFields": new_custom_fields,
                    "tags": [tag.strip() for tag in row.get(map_data.Tag).split(",")] if pd.notna(row.get(map_data.Tag)) else []
                }

                response = create_contact(contact_payload, access_token)
                if response.get("statusCode", 200) >= 400:
                    # Duplicate → update instead of counting as error
                    if (
                        response.get("message") == "This location does not allow duplicated contacts."
                        and "meta" in response
                        and "contactId" in response["meta"]
                    ):
                        duplicate_id = response["meta"]["contactId"]
                        update_payload = {"customFields": new_custom_fields}
                        update_response = update_contact(update_payload, access_token, duplicate_id)
                        if update_response.get("error"):
                            result_data["error"] += 1
                            result_data["skipped_rows"].append({
                                "row_index": idx,
                                "reason": "Duplicate found but update failed",
                                "row_data": normalized_data
                            })
                        else:
                            result_data["existing_leads"] += 1
                        continue

                    # Real error
                    result_data["error"] += 1
                    result_data["skipped_rows"].append({
                        "row_index": idx,
                        "reason": f"API error on creation: {response}",
                        "row_data": normalized_data
                    })
                    continue

                # New lead created
                result_data["new_leads"] += 1
                contact_id = response.get("contactId")
                if email_key:
                    email_to_id[email_key] = contact_id
                if phone_key:
                    phone_to_id[phone_key] = contact_id

            else:
                # Update existing lead
                populated_fields = custom_field_values
                update_data = {"customFields": populated_fields}
                response = update_contact(update_data, access_token, contact_id)
                if response.get("error"):
                    result_data["error"] += 1
                    result_data["skipped_rows"].append({
                        "row_index": idx,
                        "reason": "API error on update",
                        "row_data": normalized_data
                    })
                    continue
                result_data["existing_leads"] += 1

        except Exception as e:
            result_data["error"] += 1
            result_data["skipped_rows"].append({
                "row_index": idx,
                "reason": f"Unhandled exception: {str(e)}",
                "row_data": normalized_data
            })
    print("\nSkipped rows info:")
    for skipped in result_data["skipped_rows"]:
        print(f"Row {skipped['row_index']}: {skipped['reason']}")
        print(f"Data: {skipped['row_data']}")
        print("-" * 40)

    return result_data


@router.post("/county-stream/upload-data")
async def create_county_stream_contact(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in request body: {str(e)}")

    # Extract location_id
    location_id = "DW2nJUxi905AXIkYxfS6"
    if not location_id:
        return {"error": "location_id is required"}

    # Extract phones dynamically
    phones = []
    i = 0
    phone_number= body.get(f"phone_{i}") if body.get(f"phone_{i}") else None
    email = body.get("email","")
    name=body.get(f"phone_{i}_verification_name") if body.get(f"phone_{i}_verification_name") else ""
    if not phone_number and not email:
        return {"error": "Either phone or email is required"}

    # Extract auction info
    auction_info_keys = [
        "auction_date", "owner_1_mailing_address", "apn", 
        "lot_size_sqft", "loan_1_balance", "assessor_url", 
        "notice_of_trustee_sale", "email","address","city","state","zip","property_address_map"
    ]
    auction_info = {k: body[k] for k in auction_info_keys if k in body}

    # Optional: convert auction_date to datetime
    try:
        token = get_valid_token(location_id)
        is_duplicate=  check_duplicates(token,location_id,email,phone_number)
        print(is_duplicate)
    
        result = await get_custom_fields(location_id, token)
        custom_fields = result.get("customFields", [])
        custom_field_id_map = {f['name'].strip(): f["id"] for f in custom_fields}

        general_property_fields = {
            "Auction Date": auction_info.get("auction_date"),
            "Owner 1 Mailing Address": auction_info.get("owner_1_mailing_address"),
            "Property Address": auction_info.get("address"),
            "Loan 1 Balance": auction_info.get("loan_1_balance"),
            "APN": auction_info.get("apn"),
            "Lot Size Sqft": auction_info.get("lot_size_sqft"),
            "Assessor URL": auction_info.get("assessor_url"),
            "Notice of Trustee Sale": auction_info.get("notice_of_trustee_sale"),

        }
        i = 0
        phone_lists=[]
        phone_data={}
        while f"phone_{i}" in body:
            phone = body.get(f"phone_{i}", "").strip()
            phone_type = body.get(f"phone_{i}_type", "Mobile").strip()

            if phone:  # only add if phone exists
                phone_lists.append({
                    "phone": phone,
                    "type": phone_type
                })
            
            i += 1
        print("phone lists",phone_lists)
        new_custom_fields = []
        created_fields = []
        for key, val in general_property_fields.items():
            if key in custom_field_id_map and val is not None:

                new_custom_fields.append({"id": custom_field_id_map[key], "value": val})    

        contact_payload = {
            "firstName": name.split(" ")[0] if name and " " in name else name,
            "lastName": name.split(" ")[-1] if name and " " in name else "",
            "fullName": name,
            "email": email,
            "phone": phone_number,
            "locationId": location_id,
            "customFields": new_custom_fields,
        }
        print("contact payload",contact_payload)
        if is_duplicate:
            contact_payload.pop("locationId", None)
            response,err= update_contacts( token, is_duplicate['id'],contact_payload)
            contact_id=is_duplicate['id']
            if not response:
                return {"error":extract_message_from_error(err)}
        else:
            response = create_contact(contact_payload, token)
        # print("Response",response)
            contact_id=response.get("contact").get("id")
        # contact_id="1234"
        result = send_update_phones(phone_lists, location_id=location_id, contact_id=contact_id)
        print("result", result)
        if "error" in result.get("ghl_response", {}):
            return {"error": result.get("ghl_response", {})["error"]}
        return {"success": True, "location_id": location_id, "status": result["status"]}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
def send_update_phones(phone_lists: list, location_id: str, contact_id: str):
    """
    Takes phone list data, location_id, and contact_id,
    then sends a request to the /update-phones endpoint.
    """
    # Validate inputs
    try:
        if not phone_lists:
            return {"error": "No phone data provided"}
        if not contact_id or not location_id:
            return {"error": "Missing contact_id or location_id"}

        # Combine all phone data into a single payload
        payload = {}

        # Merge all phone_data dicts into the payload
        print("phone_lists",phone_lists)
        

        print("📦 Payload to send:", payload)
        print("phonelist",phone_lists)
        
        # Send POST request to your FastAPI endpoint
        return update_phones_in_ghl(contact_id,location_id,phone_lists)
    except Exception as e:
        return {"error": str(e)}