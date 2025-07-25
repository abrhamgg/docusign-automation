from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from datetime import datetime as dt
from dotenv import load_dotenv
import requests
import boto3
import os
from urllib.parse import urlencode

# Load env variables
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTH_URL = os.getenv("AUTH_URL")
AWS_REGION = os.getenv("AWS_REGION")
DYNAMO_TABLE_NAME = os.getenv("DYNAMO_TABLE_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Init boto3 DynamoDB
dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
table = dynamodb.Table(DYNAMO_TABLE_NAME)

router = APIRouter()


@router.get("/connect")
def connect():
    base_url = "https://marketplace.gohighlevel.com/oauth/chooselocation"
    scope = [
        "contacts.readonly",
        "contacts.write"
    ]
    query = {
        "client_id": CLIENT_ID,
        "scope": " ".join(scope),
        "response_type": "code",
        "redirect_uri": f"{AUTH_URL}/auth/redirect"
    }
    return RedirectResponse(f"{base_url}?{urlencode(query)}")


@router.get("/redirect")
def redirect_handler(code: str):
    token_url = "https://services.leadconnectorhq.com/oauth/token"
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "user_type": "Location",
        "code": code,
        "redirect_uri": f"{AUTH_URL}/auth/redirect"
    }

    token_resp = requests.post(token_url, data=token_data)
    token_json = token_resp.json()

    # Check for errors
    if "access_token" not in token_json:
        return {"error": "Token exchange failed", "details": token_json}

    access_token = token_json["access_token"]
    refresh_token = token_json["refresh_token"]
    expires_in = token_json["expires_in"]
    location_id = token_json["locationId"]

    # Fetch location details
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }

    location_resp = requests.get(
        f"https://services.leadconnectorhq.com/locations/{location_id}",
        headers=headers
    )
    location_data = location_resp.json()

    # Upsert logic: insert or update location_id entry
    now_ts = round(dt.now().timestamp())
    expires_at = str(now_ts + token_json["expires_in"])

    # Build the base item
    item = {
        "location_id": location_id,
        "token": access_token,
        "refresh": refresh_token,
        "expires_at": expires_at
    }

    # Check if location_id already exists
    existing = table.get_item(Key={"location_id": location_id}).get("Item")

    if existing:
        # 🟡 Update token + refresh + expires
        print(f"[INFO] Location {location_id} already exists. Updating tokens.")
        table.update_item(
            Key={"location_id": location_id},
            UpdateExpression="SET token = :t, refresh = :r, expires_at = :e",
            ExpressionAttributeValues={
                ":t": access_token,
                ":r": refresh_token,
                ":e": expires_at
            }
        )
    else:
        # 🟢 New user — insert full item
        print(f"[INFO] New location connected: {location_id}")
        table.put_item(Item=item)
