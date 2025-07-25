import requests
import jwt
import time
from datetime import datetime as dt, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from app.core.config import settings
from app.domain.models.docusign_models import EnvelopeData

class DocuSignAPI:
    """
    A class to handle all communications with the DocuSign eSignature REST API.
    """

    def __init__(self):
        """
        Initializes the DocuSignAPI client with configuration from settings.
        """
        self.integration_key = settings.DOCUSIGN_INTEGRATION_KEY
        self.user_id = settings.DOCUSIGN_USER_ID
        self.account_id = settings.DOCUSIGN_ACCOUNT_ID
        self.oauth_base_url = settings.DOCUSIGN_OAUTH_BASE_URL
        self.api_base_url = settings.DOCUSIGN_API_BASE_URL
        self.private_key = settings.PRIVATE_KEY

    def _generate_access_token(self) -> str | None:
        """
        Generates a JWT and exchanges it for a DocuSign access token.
        """
        try:
            payload = {
                "iss": self.integration_key,
                "sub": self.user_id,
                "aud": self.oauth_base_url.replace("https://", ""),
                "iat": int(time.time()),
                "exp": int(time.time()) + 3600,  # Token expires in 1 hour
                "scope": "signature impersonation"
            }

            private_key_bytes = self.private_key.encode('utf-8')
            private_key = serialization.load_pem_private_key(
                private_key_bytes,
                password=None,
                backend=default_backend()
            )

            encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")

            token_url = f"{self.oauth_base_url}/oauth/token"
            data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": encoded_jwt
            }

            response = requests.post(token_url, data=data)
            response.raise_for_status()

            return response.json().get("access_token")

        except Exception as e:
            # In a real app, you would log this error
            print(f"Error generating DocuSign access token: {e}")
            return None

    def get_template(self, template_name: str, access_token: str) -> dict | None:
        """
        Retrieves a specific template by its name.
        """
        url = f"{self.api_base_url}/accounts/{self.account_id}/templates"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"search_text": template_name}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            templates = response.json().get("envelopeTemplates", [])
            
            for template in templates:
                if template.get("name") == template_name:
                    return template
            return None
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching templates: {e}")
            return None

    def _valid_day(self, day_str: str) -> str:
        """
        Calculates a valid closing date, avoiding weekends.
        """
        date_obj = dt.strptime(day_str, '%Y-%m-%d')
        date_obj += timedelta(days=30)
        
        if date_obj.weekday() == 6: # Sunday
            date_obj += timedelta(days=1)
        elif date_obj.weekday() == 5: # Saturday
            date_obj -= timedelta(days=1)
            
        return date_obj.strftime("%B %d, %Y")

    def create_and_send_envelope(self, envelope_data: EnvelopeData) -> dict:
        """
        Constructs and sends an envelope using a specific template and data.
        """
        access_token = self._generate_access_token()
        if not access_token:
            raise ConnectionError("Failed to generate DocuSign access token.")

        template = self.get_template(envelope_data.templateName, access_token)
        if not template:
            raise ValueError(f"Template '{envelope_data.templateName}' not found.")
        
        template_id = template["templateId"]

        # --- Logic adapted from the original `createEnvelope` function ---

        companys = {
            "Florida": ["AMZ Title", "8381 N. Gunn Hwy Tampa,FL 33626", "813-200-6130", "neworders@amztitle.com"],
            "Louisiana": ["True Title", "110 Veterans Blvd. Suite 525, Metairie, LA 70005", "(504) 309-1030", "rlarousse@truetitle.net"],
            "Midwest": ["Empora Title", "145 E Rich St, Floor 4 Columbus, OH 43215", "(614) 660-5503", "info@emporatitle.com"],
            "Arizona": ["1st Option Title", "7975 N. Hayden Road, Suite A-200 Scottsdale, AZ 85258", "(480)-795-3491", "carrie@1stoptiontitle.com"],
            "Texas": ["Hudly Title", "801 Barton Springs Road Austin, TX 7870", "(512) 400-4210", "escrow@hudlytitle.com"],
            "Georgia": ["Parkway Law Group", "1755 North Brown Road Suite 150, Lawrenceville, GA 30043", "(678) 407-5555","brionna@parkwaytitle.com" ],
            "Kane Title":["Kane Title, Atten: Brittany", "5301 Village Creek Drive, Suite A, Plano, Texas 75093","(972) 325-1505","orders@kanetitlellc.com"],
            # abrreviated state names
            "FL": ["AMZ Title", "8381 N. Gunn Hwy Tampa,FL 33626", "813-200-6130", "neworders@amztitle.com"],
            "LA": ["True Title", "110 Veterans Blvd. Suite 525, Metairie, LA 70005", "(504) 309-1030", "rlarousse@truetitle.net"],
            "MW": ["Empora Title", "145 E Rich St, Floor 4 Columbus, OH 43215", "(614) 660-5503", "info@emporatitle.com"],
            "AZ": ["1st Option Title", "7975 N. Hayden Road, Suite A-200 Scottsdale, AZ 85258", "(480)-795-3491", "carrie@1stoptiontitle.com"],
            "TX": ["Hudly Title", "801 Barton Springs Road Austin, TX 7870", "(512) 400-4210", "escrow@hudlytitle.com"],
            "GA": ["Parkway Law Group", "1755 North Brown Road Suite 150, Lawrenceville, GA 30043", "(678) 407-5555","brionna@parkwaytitle.com" ],
            "KT": ["Kane Title, Atten: Brittany", "5301 Village Creek Drive, Suite A, Plano, Texas 75093","(972) 325-1505","orders@kanetitlellc.com"]
        }

        # Tab mappings for different templates
        texas_purchase_contract_tabs = {
            "fullNameTabs":{"FullName":["Text ac3aaeb0-0679-4b1c-8810-0c24ef969808","Name bad5d7d1-d668-4d77-b525-f789f28930f9"]},
            "textTabs":{
                "FullName":["Text 3af59d6f-3c3a-4fd4-a7b8-f3a3cd3ccd51"],
                "ClientEmail":["Text db5edea4-60d7-47bb-b690-5898bef99cc5"],
                "propertyAddress":["Text 8d063961-178b-4c61-a81e-d444a6c56978","Text 1a9f762b-0095-41a5-843a-0acc2850450e"],
                "Address":["Text b6d420a3-c43d-4bca-a07d-0924053c26a0"],
                "Seller1":["Text 2e108362-fc9a-4cab-91dc-578b5169bc58","Text 45d3e6ae-ef41-4cd3-8ce5-060456a856b4","Text 3150fd93-12fe-4675-a697-45c1db7facae","Text 9757dbfe-74ad-498a-a41e-4edafd403c8f"],
                "Seller2":["Text 8a3ef30d-601a-4f71-b108-af4041d67b7b","Text 8b3e05be-85a4-47b0-96ce-c95ed88aab4e","Text eb611128-2a6f-48c4-a4a9-8558b6e5af45","Text 9e729bce-1a7b-46e6-b9b5-e78fcaf41513"],
                "Day":["Text efd6729e-653d-4dc5-9eb5-6ba2b4afce7c",],
                "Year":["Text 2e813665-22d3-4bdc-bcaa-7b505dd567d5"],
                "Apn":["Text 33976459-a290-4365-8bcc-52b6132ea716",],
                "LegalDescription":["Text d4b9e8b5-9b87-4e07-a618-12bcc3d61ca9"],
                "Debt":["Text 72492c39-9afa-4008-bd82-75ff96a393c1","Text a829029c-a0b5-4f14-a891-1893793b6a1e","Text b0aefea7-7f48-4a17-b882-123b95ffc445", "Text d4047e56-f49f-4f80-8bb7-ffeafe60f121"],
                "Phone":["Text d6a58bbd-a825-4b73-acb2-75c78fcf5b44"],
                "Broker":["Text 5498e23f-a693-4f95-87c7-15668099b82b"],
                "sellerCarry":["Text 8829e6fd-2cb7-425a-bfcd-4026dd2a3407","Text ab63d105-95e1-412c-998a-696be1924b5f"],
                "agentComission":["Text d47a40c5-e305-4bf2-9d0f-23327efc7dc1","Text 71be9608-14e4-4202-9641-6535ec2c0ccf"],
                "purchasePrice":["Text d880ff92-fb45-4b96-87ac-2311bb1ca6ad"],
                "solarLien":["Text 45c12c3b-51e6-4e0c-903f-28ec6f4c903b","Text 75e6f183-4111-4131-aacb-8c951466ede8","Text 6d5b60db-784f-4a81-82fb-c483fe6485de"],
                "cashToSeller":["Text 435cd2a7-605d-4e1c-b808-efcfcf576345","Text 4c7b42bd-90e8-4b1f-8ad2-d47343493296","Text ad59c80a-266a-424c-b64d-9bb7c4a0c56a"],
                "Arrears":["Text b231eabb-0627-45a6-aa26-b21f1fca082e"],
                "CompanyTitle":["Text 4d29231e-a530-47c7-a852-9afa11ca6817","Text b618a341-0f01-4e87-abee-39aa2becae06"],
                "CompanyEmail":["Text bfcdd833-8930-4a77-9a85-cc6ee3000b14"],
                "CompanyAddress":["Text 2a8fd0c2-723e-4a61-8cdc-40307e7cb447","Text 5fc5c901-2804-499f-a851-d9ec1547aa37"],
                "CompanyTelephone":["Text 8741379d-5190-4cc5-9121-775f6d814acb"],
                }      
        }

        bonus_offer_tabs = {
        "fullNameTabs":{"FullName":["Name 654afd7a-cebc-41e3-adaa-ca2a135f9227"]},
        "textTabs":{
            "propertyAddress":["Text f4fea6fc-73af-42cb-9dca-a3a89278433b", "Text 96b302b1-eac1-4494-b6a7-6e60841fbd45"],
            "FullName":[],
            "Seller1":["Text 04c8164c-e4a8-44c9-8551-edd5b50b4757","Text 2ecb670f-53f1-4c5c-88f3-2d300aaf18df","Text 96595125-399d-4f15-8a22-9f250217a58c"],
            "Seller2":["Text 1d6719de-7739-4d80-9d6f-d85a464c0ac9"],
            "Day":[],
            "Year":[],
            "LegalDescription":["Text 44d99d8d-5d3b-4cb3-b430-0d755728ac48"],
            "Debt":[""],
            "Phone":[],
            "Broker":[],
            "ClientEmail":[],
            "Address":[],
            "Apn":["Text e53e1a35-855e-4562-914f-8414f3516a7d"]

        }
    }
        seller_finance_offer_tabs ={
        "fullNameTabs":{"FullName":[]},
        "textTabs":{
            "propertyAddress":["Text 763eb56b-ac75-460a-a056-7a6e5665d6c3","Text 96b302b1-eac1-4494-b6a7-6e60841fbd45", "Text f4fea6fc-73af-42cb-9dca-a3a89278433b"],
            "FullName":[],
            "Seller1":["Text 96595125-399d-4f15-8a22-9f250217a58c","Text 4e3a6460-bc99-406c-a30e-c9ff5946d97c","Text 2ecb670f-53f1-4c5c-88f3-2d300aaf18df","Text 04c8164c-e4a8-44c9-8551-edd5b50b4757"],
            "Seller2":["Text 7c6fe0bf-8a2a-4121-90b0-59598bfedbbb","Text 1d6719de-7739-4d80-9d6f-d85a464c0ac9","Text 8d3274f5-0de3-4182-87b7-f10add7d8cdf"],
            "Day":["Text 806fb25a-9700-44ae-92d3-6858d3543322"],
            "Year":[],
            "Apn":["Text e53e1a35-855e-4562-914f-8414f3516a7d"],
            "LegalDescription":["Text 44d99d8d-5d3b-4cb3-b430-0d755728ac48"],
            "Debt":[],
            "Phone":[],
            "Broker":[],
            "ClientEmail":[],
            "Address":[],
            "CashToSeller":["Text 26cdeb5f-85f4-4dab-9a5f-4634aabee303",],
            "CompanyName":["Text fa3727e1-7aaa-437d-b4b7-289e139d3535"],
            "CompanyAddress":["Text de5818de-f9bd-4ada-b829-35f3474bdc52",],
            "CompanyTitle":["Text c95342ba-0ee8-44e7-b467-05c7371221ab"]
        }
    }

        # Prepare envelope data
        envelope_data.emailSubject = f"{envelope_data.propertyAddress} - OFFER"
        full_date = self._valid_day(dt.now().strftime("%Y-%m-%d"))
        day_part, year_part = full_date.rsplit(' ', 1)
        envelope_data.Day = day_part
        envelope_data.Year = year_part[2:]
        
        envelope_data.Seller1 = f"{envelope_data.Seller1First} {envelope_data.Seller1Last}"
        envelope_data.Seller2 = f"{envelope_data.Seller2First} {envelope_data.Seller2Last}"
        envelope_data.FullName = f"{envelope_data.FirstName} {envelope_data.LastName}"
        
        if envelope_data.Debt and envelope_data.Debt!="":
            envelope_data.Debt=envelope_data.Debt.split(".")[0][1:]
        if envelope_data.sellerCarry and envelope_data.sellerCarry!="":
            envelope_data.sellerCarry=envelope_data.sellerCarry.split(".")[0][1:]
        if envelope_data.cashToSeller and envelope_data.cashToSeller!="":
            envelope_data.cashToSeller=envelope_data.cashToSeller.split(".")[0][1:]
        if envelope_data.solarLien and envelope_data.solarLien!="":
            envelope_data.solarLien=envelope_data.solarLien.split(".")[0][1:]
        if envelope_data.purchasePrice and envelope_data.purchasePrice!="":
            envelope_data.purchasePrice=envelope_data.purchasePrice.split(".")[0][1:]
        if envelope_data.Arrears and envelope_data.Arrears!="":
            envelope_data.Arrears=envelope_data.Arrears.split(".")[0][1:]
        if envelope_data.agentComission and envelope_data.agentComission!="":
            envelope_data.agentComission=envelope_data.agentComission.split(".")[0][1:]
        if envelope_data.CashToSeller and envelope_data.CashToSeller!="":
            envelope_data.CashToSeller=str(envelope_data.CashToSeller)+" "+"cash to the sellers at COE."
            
        # Select the correct tab mapping
        tab_mappings = {}
        if envelope_data.templateName == "Cash Offers-(Bonus Offers)":
            tab_mappings = bonus_offer_tabs
        elif envelope_data.templateName == "Seller Finance Offer":
            tab_mappings = seller_finance_offer_tabs
        else: # Default to Texas-Creative Purchase Contract Hudly Title
            tab_mappings = texas_purchase_contract_tabs

        # Set dynamic company info for relevant templates
        if envelope_data.state in companys:
            company_info = companys[envelope_data.state]
            envelope_data.CompanyTitle = company_info[0]
            envelope_data.CompanyAddress = company_info[1]
            envelope_data.CompanyTelephone = company_info[2]
            envelope_data.CompanyEmail = company_info[3]

        # Build the tabs structure
        tabs = {"textTabs": [], "fullNameTabs": []}
        for tab_type, fields in tab_mappings.items(): # iteration of two
            for field_name, tab_ids in fields.items():
                field_value = getattr(envelope_data, field_name, "")
                if field_value and field_value not in ["N/A", "None"]:
                    for tab_id in tab_ids:
                        # Add custom logic for specific tabs
                        if tab_id=="Text 4c7b42bd-90e8-4b1f-8ad2-d47343493296" and field_value=="cashToSeller":
                            field_value = f'•${envelope_data.cashToSeller} Cash to the sellers at COE.'
                        elif tab_id == "Text 8829e6fd-2cb7-425a-bfcd-4026dd2a3407" and field_value == "sellerCarry":
                            field_value = f'•${envelope_data.sellerCarry} Seller carry to be paid to the sellers in 48 equal payments of $166.67 per month.'
                        elif tab_id == "Text 75e6f183-4111-4131-aacb-8c951466ede8" and field_value == "solarLien":
                            field_value = f'•${envelope_data.solarLien}  Solar lien to be taken over subject to the existing loan.'
                        elif tab_id == "Text 71be9608-14e4-4202-9641-6535ec2c0ccf" and field_value == "agentComission":
                            field_value = f'•${envelope_data.agentComission}  Listing agent commission paid by buyer at COE.'
                        elif tab_id == "Text b231eabb-0627-45a6-aa26-b21f1fca082e" and field_value == "Arrears":
                            field_value = f'•${envelope_data.Arrears} In seller arrears to be paid by buyer at COE.'
                        elif tab_id == "Text 72492c39-9afa-4008-bd82-75ff96a393c1" and field_value == "Debt":
                            field_value = f'existing loan of ${envelope_data.Debt}'
                        elif tab_id == "Text 6d5b60db-784f-4a81-82fb-c483fe6485de" and field_value == "solarLien":
                            field_value = f"Solar lien of ${envelope_data.solarLien}"

                        tabs[tab_type].append({"tabLabel": tab_id, "value": field_value})
        
        # Construct the final envelope payload
        envelope_payload = {
            "emailSubject": envelope_data.emailSubject,
            
            "status": "created",
            "compositeTemplates": [
                {
                    "serverTemplates": [
                        {
                            "sequence": "1",
                            "templateId": template_id
                        }
                    ],
                    "inlineTemplates": [
                        {
                            "sequence": "1",
                            "recipients": {
                                "signers": [
                                    {
                                        "roleName": "Signer 1", 
                                        "recipientId": "f5d6f049-efc9-4fa1-9611-618063ed473d",
                                        "name": "Gordon Sran",
                                        "email": "gordon@palmcapitalventures.com",
                                        "tabs": tabs
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        # Send the request to DocuSign
        url = f"{self.api_base_url}/accounts/{self.account_id}/envelopes"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = requests.post(url, headers=headers, json=envelope_payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Log the error and the response body for debugging
            print(f"Error creating envelope: {e}")
            print(f"Response body: {e.response.text}")
            raise ConnectionError(f"Failed to create DocuSign envelope. Error: {e.response.text}")