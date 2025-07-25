import requests
from datetime import datetime as dt
from cryptography.fernet import Fernet
from app.core.config import settings
from app.infrastructure.database.repository import ConnectionRepository

class REICBAPI:
    """
    Handles all communication with the REICB (GoHighLevel) API,
    including authentication and token management.
    """
    def __init__(self, connection_repo: ConnectionRepository):
        self.repo = connection_repo
        self.base_url = settings.REICB_API_BASE_URL
        self.fernet = Fernet(settings.ENC_KEY.encode())

    def _get_valid_access_token(self, location_id: str) -> str:
        """
        Retrieves the access token for a location, refreshing it if necessary.
        This internal method replaces the check_and_refresh_token decorator.
        """
        connection = self.repo.get_connection(location_id)
        if not connection:
            raise ConnectionError(f"No connection found for location ID: {location_id}")

        current_time = int(dt.now().timestamp())
        if current_time < int(connection.expires):
            # Token is valid, decrypt and return it
            return self.fernet.decrypt(connection.token.encode()).decode()

        # Token has expired, refresh it
        print(f"Token expired for location {location_id}. Refreshing...")
        decrypted_refresh_token = self.fernet.decrypt(connection.refresh.encode()).decode()

        try:
            response = requests.post(
                settings.REICB_OAUTH_URL,
                data={
                    "client_id": settings.REICB_CLIENT_ID,
                    "client_secret": settings.REICB_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": decrypted_refresh_token,
                    "user_type": "Location",
                    "redirect_uri": settings.REICB_REDIRECT_URL,
                }
            )
            response.raise_for_status()
            token_data = response.json()

            # Update connection object with new, encrypted tokens
            connection.expires = str(round(dt.now().timestamp() + token_data["expires_in"]))
            connection.token = self.fernet.encrypt(token_data["access_token"].encode()).decode()
            connection.refresh = self.fernet.encrypt(token_data["refresh_token"].encode()).decode()
            self.repo.save_connection(connection)

            print(f"Successfully refreshed token for location {location_id}.")
            return token_data["access_token"]

        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else "No response"
            print(f"Failed to refresh token for location {location_id}: {error_details}")
            raise ConnectionError(f"Failed to refresh token. Please re-link your account. Details: {error_details}")

    def _make_request(self, method: str, endpoint: str, location_id: str, **kwargs) -> dict:
        """A helper method to execute authenticated requests."""
        access_token = self._get_valid_access_token(location_id)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Version": "2021-07-28",
            "Accept": "application/json"
        }
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(method, url, headers=headers, timeout=15, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error for {method} {url}: {e}")
            raise ConnectionError(f"API request failed: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Network Error for {method} {url}: {e}")
            raise ConnectionError(f"A network error occurred: {e}")

    def fetch_contact_by_id(self, contact_id: str, location_id: str) -> dict:
        """Fetches a single contact by their ID."""
        response_data = self._make_request("GET", f"contacts/{contact_id}", location_id)
        return response_data.get('contact', {})

    def get_contact_details(self, contact: dict, location_id: str) -> dict:
        """
        Takes a contact object and returns a dictionary of its custom fields
        with human-readable names instead of IDs.
        """
        custom_fields_data = self._make_request("GET", f"locations/{location_id}/customFields", location_id)
        
        id_to_name_map = {
            field['id']: field['name']
            for field in custom_fields_data.get("customFields", [])
            if 'id' in field and 'name' in field
        }

        # Use the provided 'replace_ids_with_names' logic
        processed_fields = {}
        for field in contact.get('customFields', []):
            field_id = field.get('id')
            if field_id in id_to_name_map:
                field_name = id_to_name_map[field_id]
                processed_fields[field_name] = field.get('value')

        return processed_fields