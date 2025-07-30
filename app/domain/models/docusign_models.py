from pydantic import BaseModel, Field
from datetime import datetime

class EnvelopeData(BaseModel):
    templateName: str = ""
    emailSubject: str = ""
    roleName: str = "Signer 1"
    status: str = "created"
    FirstName: str = ""
    LastName: str = ""
    documentName: str = ""
    contactId: str = ""
    Company: str = ""
    Date: str = ""
    Address: str = ""
    ClientEmail: str = ""
    propertyAddress: str = ""
    Seller1: str = ""
    Seller2: str = ""
    Seller1First: str = ""
    Seller1Last: str = ""
    Seller2First: str = ""
    Seller2Last: str = ""
    Day: str = ""
    Year: str = Field(default_factory=lambda: datetime.now().strftime("%y"))
    Apn: str = ""
    LegalDescription: str = ""
    Debt: str = ""
    Phone: str = ""
    Broker: str = ""
    FullName: str = ""
    sellerCarry: str = ""
    agentComission: str = ""
    purchasePrice: str = ""
    solarLien: str = ""
    cashToSeller: str = ""
    Arrears: str = ""
    CompanyName: str = ""
    CashToSeller: str = ""
    CompanyTitle: str = ""
    CompanyEmail: str = ""
    CompanyAddress: str = ""
    CompanyTelephone: str = ""
    city_name: str = ""
    state: str = ""

class Property(BaseModel):
    id: str
    reicb_url: str | None = None
    cash_to_seller: float | None = None
    seller_carry_terms: str | None = None
    agent_commission: float | None = None
    debt: float | None = None
    contract_price: float | None = None