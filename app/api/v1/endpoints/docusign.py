from fastapi import APIRouter, Depends, HTTPException
from app.api.v1.schemas.docusign_schemas import SendEnvelopeRequest, SendEnvelopeResponse
from app.domain.services.docusign_service import DocusignService
from app.dependencies import get_docusign_service 

router = APIRouter()

@router.post("/send_envelope", response_model=SendEnvelopeResponse)
def send_envelope(
    payload: SendEnvelopeRequest,
    docusign_service: DocusignService = Depends(get_docusign_service)
):
    try:
        result = docusign_service.send_envelope_for_property(
            customer_id=payload.customer_id,
            property_id=payload.property_id,
            location_id=payload.location_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")