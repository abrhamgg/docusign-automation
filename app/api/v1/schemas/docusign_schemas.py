from pydantic import BaseModel

class SendEnvelopeRequest(BaseModel):
    customer_id: str
    property_id: str
    location_id: str

class SendEnvelopeResponse(BaseModel):
    status: str
    envelopeId: str