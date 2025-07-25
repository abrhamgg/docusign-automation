from datetime import datetime as dt, timedelta
from app.domain.models.docusign_models import EnvelopeData
from app.infrastructure.external.docusign_api import DocuSignAPI
from app.infrastructure.external.reicb_api import REICBAPI
from app.infrastructure.database.repository import PropertyRepository

def is_number(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

def format_currency(value):
    if not is_number(value):
        return None
    return f"${float(value):,.0f}"

class DocusignService:
    def __init__(self, docusign_api: DocuSignAPI, reicb_api: REICBAPI, property_repo: PropertyRepository):
        """
        Initializes the service with its dependencies (the infrastructure components).
        """
        self.docusign_api = docusign_api
        self.reicb_api = reicb_api
        self.property_repo = property_repo

    def send_envelope_for_property(self, customer_id: str, property_id: str, location_id: str) -> dict:
        """
        The main business logic method. It orchestrates the entire process.
        """
        # 1. Coordinate with Infrastructure: Get data from the database
        property_dict = self.property_repo.get_property_by_id(customer_id, property_id)
        if not property_dict:
            raise ValueError(f"Property with ID '{property_id}' not found for customer '{customer_id}'.")

        # 2. Enforce Business Rule
        if not property_dict.get("reicb_url"):
            raise ValueError("Property does not have a linked REICB contact URL.")
        
        contact_id = property_dict["reicb_url"].split("/")[-1]

        # 3. Coordinate with Infrastructure: Get data from an external API
        contact = self.reicb_api.fetch_contact_by_id(contact_id, location_id)
        contact_details = self.reicb_api.get_contact_details(contact, location_id)

        if not contact_details:
            raise ValueError("Failed to retrieve contact details from REICB.")

        # 4. Data Transformation: Map all data into our domain model
        envelope = self._create_envelope_data(contact_details, property_dict, contact)
        
        # 5. Enforce Business Rule: Determine the template name
        envelope.templateName = self._get_template_name(contact_details) or 'Texas-Creative Purchase Contract Hudly Title'
        
        # 6. Enforce Business Rule: Set contact_id
        envelope.contactId = contact_id
        
        # 7. Coordinate with Infrastructure: Execute the final action
        return self.docusign_api.create_and_send_envelope(envelope)

    def _create_envelope_data(self, contact_details: dict, property_dict: dict, contact: dict) -> EnvelopeData:
        """Helper method for data mapping and transformation."""
        
        # This mapping is an important piece of business logic
        MAPPING_DICTIONARY = {
            'MLS Agent Name': 'FullName',
            'Owner 1 First Name ': 'Seller1First',
            'Owner 1 Last Name ': 'Seller1Last',
            'Owner 2 First Name ': 'Seller2First',
            'Owner 2 Last Name ': 'Seller2Last',
            'MLS Agent Phone': 'Phone',
            'MLS Agent E-Mail': 'Email',
            'MLS Agent E-Mail': 'ClientEmail',
            'MLS Brokerage Name': 'Broker',
            'APN': 'Apn',
            # 'Year Built': 'Year',
            'Loan 1 Balance': 'Debt',
            'Listing Agent Commision': 'agentComission',
            'Cash to seller': 'CashToSeller',
            'Property Address': 'Address',
            'Property City': 'city_name',
            'Property State': 'state',
            'Legal Description': 'LegalDescription',
            'Property Address Map': 'propertyAddress'
        }


        envelope_data_dict = {}
        for key, attribute in MAPPING_DICTIONARY.items():
            if key in contact_details:
                envelope_data_dict[attribute] = contact_details[key]

         # Further enrich and format data
        envelope_data_dict['FirstName'] = contact.get('firstName', '')
        envelope_data_dict['LastName'] = contact.get('lastName', '')
        envelope_data_dict['CashToSeller'] = format_currency(envelope_data_dict.get('CashToSeller')) or format_currency(property_dict.get('cash_to_seller'))
        envelope_data_dict['companyName'] = contact.get('companyName', '')
        envelope_data_dict['sellerCarry'] = envelope_data_dict.get('sellerCarry') or property_dict.get('seller_carry_terms', '')
        envelope_data_dict['Debt'] = format_currency(envelope_data_dict.get('Debt')) or format_currency(property_dict.get('debt', ''))
        envelope_data_dict['purchasePrice'] = format_currency(property_dict.get('contract_price', ''))
        envelope_data_dict['agentComission'] = format_currency(envelope_data_dict.get('agentComission')) or format_currency(property_dict.get('agent_commission', ''))
        
        envelope = EnvelopeData(**envelope_data_dict)

       


        return envelope

    def _get_template_name(self, contact_detail: dict) -> str | None:
        """Contains the business logic for selecting a template."""
        doc_type = contact_detail.get('Document Type', '')
        if "Subto Contract" in doc_type and "Seller finance Contract" not in doc_type:
            return "Texas-Creative Purchase Contract Hudly Title"
        elif "Seller finance Contract" in doc_type and "Subto Contract" not in doc_type:
            return "Seller Finance Offer"
        elif "Subto Contract" in doc_type and "Seller finance Contract" in doc_type:
            return "Cash Offers-(Bonus Offers)"
        else:
            return None