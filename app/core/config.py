import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # REICB API / GoHighLevel Configuration
    REICB_API_BASE_URL: str = os.getenv("REICB_API_BASE_URL")
    REICB_OAUTH_URL: str = os.getenv("REICB_OAUTH_URL")
    REICB_CLIENT_ID: str = os.getenv("REICB_CLIENT_ID")
    REICB_CLIENT_SECRET: str = os.getenv("REICB_CLIENT_SECRET")
    REICB_REDIRECT_URL: str = os.getenv("REICB_REDIRECT_URL")

    # Fernet Encryption Key
    ENC_KEY: str = os.getenv("ENC_KEY")

    # GHL / LeadConnector settings (used by dueIn webhook integration)
    GHL_API_TOKEN: str = os.getenv("GHL_API_TOKEN") or os.getenv("GHL_ACCESS_TOKEN")
    GHL_ACCESS_TOKEN: str = os.getenv("GHL_ACCESS_TOKEN")
    GHL_BASE_URL: str = os.getenv("GHL_BASE_URL", "https://services.leadconnectorhq.com")
    GHL_API_VERSION: str = os.getenv("GHL_API_VERSION", "2021-07-28")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # DocuSign Configuration
    DOCUSIGN_INTEGRATION_KEY: str = os.getenv("DOCUSIGN_INTEGRATION_KEY")
    DOCUSIGN_USER_ID: str = os.getenv("DOCUSIGN_USER_ID")
    DOCUSIGN_ACCOUNT_ID: str = os.getenv("DOCUSIGN_ACCOUNT_ID")
    DOCUSIGN_OAUTH_BASE_URL: str = os.getenv("DOCUSIGN_OAUTH_BASE_URL")
    DOCUSIGN_API_BASE_URL: str = os.getenv("DOCUSIGN_API_BASE_URL")
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY")

    # AWS DynamoDB Configuration
    DYNAMODB_PREFIX: str = os.getenv("DYNAMODB_PREFIX", "homedispo")
    DYNAMODB_REGION: str = os.getenv("DYNAMODB_REGION", "us-east-2")
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")


settings = Settings()

# Add a check to ensure the encryption key is set
if not settings.ENC_KEY:
    raise ValueError("The 'ENC_KEY' environment variable must be set for encryption.")