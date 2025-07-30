from app.domain.services.docusign_service import DocusignService
from app.infrastructure.database.repository import PropertyRepository, ConnectionRepository
from app.infrastructure.external.docusign_api import DocuSignAPI
from app.infrastructure.external.reicb_api import REICBAPI

# --- Step 2: Create Singleton instances of our infrastructure ---
# These objects are created once and shared across the entire application.
# This is efficient and manages state in a single place.

# Database Repositories
property_repository = PropertyRepository()
connection_repository = ConnectionRepository()

# External API Clients
docusign_api_client = DocuSignAPI()
reicb_api_client = REICBAPI(connection_repo=connection_repository)


# --- Step 3: Create the "Getter" function for our service ---
# This function will be called by FastAPI for each request that needs it.
# It assembles the service with its dependencies.

def get_docusign_service() -> DocusignService:
    """
    Dependency injector for the DocusignService.
    
    Instantiates the service with its required infrastructure components.
    FastAPI's `Depends` will use this function to provide a fully
    configured service instance to the API endpoints.

    Returns:
        An instance of DocusignService.
    """
    return DocusignService(
        docusign_api=docusign_api_client,
        reicb_api=reicb_api_client,
        property_repo=property_repository
    )