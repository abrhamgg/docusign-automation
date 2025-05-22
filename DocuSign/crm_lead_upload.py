from fastapi import HTTPException, UploadFile, File, Form


from urllib.parse import urlencode
from pydantic import BaseModel
from fastapi import APIRouter

import requests
import uvicorn
import pandas as pd
import json


router = APIRouter(prefix='/crm')

# In-memory storage for tokens (use a database in production)
tokens = {"access_token":"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdXRoQ2xhc3MiOiJMb2NhdGlvbiIsImF1dGhDbGFzc0lkIjoidXBkdzNJZHd2cWVaSmVmQzduWmciLCJzb3VyY2UiOiJJTlRFR1JBVElPTiIsInNvdXJjZUlkIjoiNjZiMTUxMTM4OGY2OWExOWExZDk5NTZkLWx6aGtkdTQ5IiwiY2hhbm5lbCI6Ik9BVVRIIiwicHJpbWFyeUF1dGhDbGFzc0lkIjoidXBkdzNJZHd2cWVaSmVmQzduWmciLCJvYXV0aE1ldGEiOnsic2NvcGVzIjpbImxvY2F0aW9ucy9jdXN0b21WYWx1ZXMud3JpdGUiLCJsb2NhdGlvbnMvY3VzdG9tRmllbGRzLndyaXRlIiwibG9jYXRpb25zL2N1c3RvbUZpZWxkcy5yZWFkb25seSIsImxvY2F0aW9ucy5yZWFkb25seSIsImNvbnRhY3RzLnJlYWRvbmx5IiwibG9jYXRpb25zL2N1c3RvbVZhbHVlcy5yZWFkb25seSIsImNvbnRhY3RzLndyaXRlIiwiY29udGFjdHMucmVhZG9ubHkiLCJjb252ZXJzYXRpb25zL21lc3NhZ2Uud3JpdGUiLCJjb252ZXJzYXRpb25zL21lc3NhZ2UucmVhZG9ubHkiLCJ1c2Vycy5yZWFkb25seSIsInVzZXJzLndyaXRlIl0sImNsaWVudCI6IjY2YjE1MTEzODhmNjlhMTlhMWQ5OTU2ZCIsInZlcnNpb25JZCI6IjY2YjE1MTEzODhmNjlhMTlhMWQ5OTU2ZCIsImNsaWVudEtleSI6IjY2YjE1MTEzODhmNjlhMTlhMWQ5OTU2ZC1semhrZHU0OSJ9LCJpYXQiOjE3NDc3ODQ5MDcuMTkyLCJleHAiOjE3NDc4NzEzMDcuMTkyfQ.V1NGP_3he7RD-VcyXmfg-EPjJyfeZpfiHayuZzX24XTlwhI2d8UFK25aalRNswji_yu4_6QjatKcpfDxBdK4z2S4pDNRhPaSi9xNvUOMT65qiB1FcQzI8ziBaxMoaooRoCAmjOvdthVbMxLQ9BYo8LTFVB3ffI46q38z2RBog0XyzdGSx0bR38MvQYmHvVHSFENvuAF6Ws5kmCOnzusDvyVkWdx8o92fDhrbMFL0So0K6p8fsYLYu9ZRZ-JqoIw4mHoRLrDzvJDy7-HKR346dg4bBIE7G2lrFPQuLFY8SdjsdWs0ys0VHo7c4v4OKV3qYEKLtLgbhQdiV1F9xLV45NiXPtpoOOgXBX6luVclnlI-kK4ZdMWaIgwryt4n7bOu0lb1Js_kTQfzBd5GRqZ65PFwMlz1N9E8uPgj6DBH3x76611H8WMhfAHZeq4mrxj83UKxzdDIm-mJWAyR2ipsQcy4Y-kgHjx3M02J0uttee2HoVusU1qgCET6LLs3k3KvllE92pORDbMoFKLgdyvg8BLUCsidIFI9lnmDP901mFNGfF7-oQyQb8E1t5WFSw8PbA6FH_i41zYUzfjXcJdkTTBqLQdBy5zWn5a2H9rDaMmjRT_fbg6paubrrLfoTmxy94scuAFGzL4oX06yXSqVPREslKckR9LJ2VmFvqKsKMc"}

class NameMap(BaseModel):
    """
    Model for mapping crm name to the input csv file.
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


def get_access_token():
    return tokens.get("access_token")

def create_contact(data,access_token):
    url = f"https://services.leadconnectorhq.com/contacts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def update_contact(data,access_token, contactId):
    url = f"https://services.leadconnectorhq.com/contacts/{contactId}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }
    response = requests.put(url, headers=headers, json=data)
    return response.json()

async def get_custom_fields(locationId: str):
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token available")
    
    url =f"https://services.leadconnectorhq.com/locations/{locationId}/customFields"
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
    
    

@router.post("/upload-contact")
async def createContact(locationId:str,access_token:str = Form(...), map_data: str = Form(...) , members_file: UploadFile = File(...), new_members_file: UploadFile = File(...)):
    try:
        map_data_dict = json.loads(map_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for map_data")

    # Validate the dictionary against the NameMap model
    try:
        map_data = NameMap(**map_data_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid mapping data: {str(e)}")
    
    
    
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token available")
    
    email_phone_contactId_map = {}

    # Read the uploaded files
    members_df = pd.read_csv(members_file.file, index_col=False)
    leads_df = pd.read_csv(new_members_file.file, index_col=False)

    # Process the members file
    for index, row in members_df.iterrows():
        email = row.get("Email")
        phone = row.get("Phone")
        contactId = row.get("Contact Id")
        if email:
            email_phone_contactId_map[email] = contactId
        if phone:
            email_phone_contactId_map[phone] = contactId

    result = await get_custom_fields(locationId)
    custome_fields = result.get("customFields")

    if not custome_fields:
        raise HTTPException(status_code=400, detail="No custom fields available")
    
    # Create a mapping of custom field names to their IDs
    property_address_custome_fields ={field['name']:field["id"] for field in custome_fields if field["name"].startswith("Property")}

    # Put custom fields in a list
    General_property_fields = { "Property Address":"PropertyAddress"}

    result_data = {
        'new_leads':0,
        'existing_leads':0,
        'error':0,
        'total_':0
        }
    try:
        # Process the new leads file
        for index, row in leads_df.iterrows():
            result_data['total_']+=1
            email = row.get(map_data.email)
            phone = row.get(map_data.phone)
            contactId = ""
            if email and email in email_phone_contactId_map:
                contactId = email_phone_contactId_map[email]
            elif phone and phone in email_phone_contactId_map:
                contactId = email_phone_contactId_map[phone]
            else:
                # Create a new contact
                new_custome_field = []
                for key, value in General_property_fields.items():
                    val= row.get(getattr(map_data, value))
                    if pd.notna(val) and key in property_address_custome_fields:
                        new_custome_field.append({"id":property_address_custome_fields.get(key), "value": val})

                data = {
                    "firstName": row.get(map_data.firstName),
                    "lastName": row.get(map_data.lastName),
                    "email": "" if pd.isna(email) else email,
                    "phone":  "" if pd.isna(phone) else phone,
                    "country": row.get(map_data.Country),
                    "locationId": locationId,
                    "customFields": new_custome_field,}

                response = create_contact(data, access_token)
                # Check for errors
                if response.get("error"):
                    result_data["error"] += 1
                    raise HTTPException(status_code=400, detail=f"Error creating contact: {response.get('error')}")
                result_data["new_leads"] += 1
                contactId = response.get("contactId")
                if email:
                    email_phone_contactId_map[email] = contactId
                if phone:
                    email_phone_contactId_map[phone] = contactId
                continue

            # Update the contact with the new data
            if contactId:
                populated_custome_field = []
                # get the member's contact data
                member_data= members_df[members_df["Contact Id"]==contactId]
                for i in range(2,6):
                    col_name = f"Property Address {i}"
                    # Check if the column exists and if it's empty or NaN in the first row
                    if col_name not in member_data or pd.isna(member_data[col_name].iloc[0]) or member_data[col_name].iloc[0] == "":
                        # Now populate this empty address slot
                        for key, value in General_property_fields.items():
                            val = row.get(getattr(map_data, value))
                            if pd.notna(val) and key in property_address_custome_fields:
                                map_key = f"{' '.join(key.split(' ')[:2])} {i}"
                                populated_custome_field.append({
                                    "id": property_address_custome_fields.get(map_key),
                                    "value": val
                                })
                        break  

                data = {"customFields":populated_custome_field}
                response = update_contact(data, access_token, contactId)
                if response.get("error"):
                    result_data["error"] += 1
                    raise HTTPException(status_code=400, detail=f"Error updating contact: {response.get('error')}")
                result_data["existing_leads"] += 1
        return result_data       
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error creating/updating contact: {str(e)}",result = {result_data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}",result = {result_data})
    

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)