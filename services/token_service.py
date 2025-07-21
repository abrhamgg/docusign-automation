import boto3
import os
from datetime import datetime as dt
import requests
from dotenv import load_dotenv

load_dotenv()

# Load from .env
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTH_URL = os.getenv("AUTH_URL")
AWS_REGION = os.getenv("AWS_REGION")
DYNAMO_TABLE_NAME = os.getenv("DYNAMO_TABLE_NAME")

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

table = dynamodb.Table(DYNAMO_TABLE_NAME)


def get_valid_token(location_id: str):
    # Fetch user from DynamoDB
    response = table.get_item(Key={"location_id": location_id})
    user = response.get("Item")
    if not user:
        raise Exception("No user found for that location ID")

    now = round(dt.now().timestamp())
    expires_at = int(user["expires_at"])

    # Token expired — refresh
    if now > expires_at:
        print("Access token expired, refreshing...")
        token_resp = requests.post(
            "https://services.leadconnectorhq.com/oauth/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": user["refresh"],
                "redirect_uri": f"{AUTH_URL}/auth/redirect",
                "user_type": "Location"
            }
        ).json()

        user["token"] = token_resp["access_token"]
        user["refresh"] = token_resp["refresh_token"]
        user["expires_at"] = str(round(dt.now().timestamp() + token_resp["expires_in"]))

        # Update in DynamoDB
        table.put_item(Item=user)

    return user["token"]
