from fastapi import FastAPI
from pydantic import BaseModel
import requests
import time
import jwt
from dotenv import load_dotenv
import os
from typing import Optional
from datetime import datetime,timedelta

app=FastAPI()

# Input data model
class EnvelopeData(BaseModel):
    templateName: str
    emailSubject: str
    roleName: str
    status: str
    FirstName: str
    LastName: str
    documentName: str
    contactId: str
    Company : Optional[str]=None
    Date: Optional[str]=None
    Address: Optional[str]=None
    ClientEmail: Optional[str]=None
    propertyAddress: Optional[str]=None
    
    Seller1: Optional[str]=None
    Seller2: Optional[str]=None
    Seller1First: Optional[str]=None
    Seller1Last: Optional[str]=None
    Seller2First: Optional[str]=None
    Seller2Last: Optional[str]=None
    Day: Optional[str]=None
    Year: Optional[str]=None
    Apn: Optional[str]=None
    LegalDescription: Optional[str]=None
    Debt: Optional[str]=None
    Phone: Optional[str]=None
    Broker: Optional[str]=None
    FullName: Optional[str]=None
 



#  Webhook data model
class DocusignHook(BaseModel):
    event: str
    data: dict
   
# function that generates an access token using Jwt token thst uses the private key
def generateAccessToken():
    data={
            "iss": "b4bb3953-1adf-4f59-bc99-7980812b4586", # Integration key
            "sub": "38124ca9-c32d-4eee-95fe-e5c9f14a39f3", # user id
            "aud": "account.docusign.com",
            "iat": int(time.time()),
            "exp": int(time.time()) + 36000,
            "scope": "signature impersonation"
        }
    load_dotenv()
    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    encoded_jwt = jwt.encode(data, PRIVATE_KEY, algorithm="RS256")

    url = "https://account.docusign.com/oauth/token"
   
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": encoded_jwt
    }

    response=requests.post(url,data=data)
    if "access_token" in response.json():
        return response.json()["access_token"]
    print(response.json())
    return None

# Get all the templates from the account
def getTemplates(access_token,accountID):
    url = f'https://na4.docusign.net/restapi/v2.1/accounts/{accountID}/templates'
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    return response.json()

# Get a specific template from the account using the template name
def getTemplate(templateName,access_token,accountID):
    url = f"https://na4.docusign.net/restapi/v2.1/accounts/{accountID}/templates"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    templates = response.json()["envelopeTemplates"]
    for template in templates:
        if template["name"] == templateName:
            return template
    return None

def getDocuments(templateId,accountID,accessToken):
    url = f"https://na4.docusign.net/restapi/v2.1/accounts/{accountID}/templates/{templateId}/documents"
    headers={"Authorization": f"Bearer {accessToken}"}
    response=requests.get(url,headers=headers)
    return response.json()

# Get a specific document from the template using the document name
def getDocument(documentName,access_token,templateId,accountID):
    url = f"https://na4.docusign.net/restapi/v2.1/accounts/{accountID}/templates/{templateId}/documents"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)

    documents = response.json()["templateDocuments"]

    for document in documents:
        if document["name"] == documentName:
            return document
    return None

# Get all the tabs from the document
def getDocumentTabs(documnetId,accessToken,templateId,accountID):
    url = f"https://na4.docusign.net/restapi/v2.1/accounts/{accountID}/templates/{templateId}/documents/{documnetId}/tabs"
    headers = {
        "Authorization": f"Bearer {accessToken}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    return response.json()

# Add a tag to a contact in HighLevel using the contactId 
def addTag(contactId,tag,accessToken):
    headers = {
        "Authorization": f"Bearer {accessToken}",
        "Content-Type": "application/json"
    }
    url=f"https://rest.gohighlevel.com/v1/contacts/{contactId}/tags/"
    response=requests.post(url,headers=headers,json={"tags":[tag]})
    return response.json()
def validDay(day):
    date_obj = datetime.strptime(day, '%Y-%m-%d')
    date_obj=date_obj+timedelta(days=30)
    day_of_week = date_obj.weekday()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday","Sunday"]
    day_name=days[day_of_week]
    if day_name=="Sunday":
        date=(date_obj+ timedelta(days=1)).strftime("%Y-%m-%d")
        return date
    if day_name=="Saturday":
        date=(date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
        return date
    return date_obj.strftime("%B %d %Y")

@app.get("/")
def home():
    return "Welcome to the DocuSign OAuth Backend!"

@app.post("/sendEnvelope")
def sendEnvelope(envelope_data:EnvelopeData):
    access_token =generateAccessToken()
    if not access_token:
        return "Error: Access token not generated"
    # baseURL =  "https://na4.docusign.net/restapi/v2.1/accounts"
    baseURL="https://na4.docusign.net/restapi/v2.1/accounts"

    accountID = "d793357d-2249-42c3-a21a-e99f0a993bd7"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    template=getTemplate(envelope_data.templateName,access_token,accountID)
    if not template:
        return "Error: Template not found"
    templateId=template["templateId"]
    envelope_data.FullName=envelope_data.FirstName+" "+envelope_data.LastName
    TexasPurchaseContract={
        "fullNameTabs":{"FullName":["Text ac3aaeb0-0679-4b1c-8810-0c24ef969808","Name bad5d7d1-d668-4d77-b525-f789f28930f9"]},
        "textTabs":{
            "FullName":["Text ac3aaeb0-0679-4b1c-8810-0c24ef969808","Text 3af59d6f-3c3a-4fd4-a7b8-f3a3cd3ccd51"],
            "ClientEmail":["Text db5edea4-60d7-47bb-b690-5898bef99cc5"],
            "propertyAddress":["Text 8d063961-178b-4c61-a81e-d444a6c56978","Text 1a9f762b-0095-41a5-843a-0acc2850450e"],
            "Address":["Text b6d420a3-c43d-4bca-a07d-0924053c26a0"],
            "Seller1":["Text 2e108362-fc9a-4cab-91dc-578b5169bc58","Text 45d3e6ae-ef41-4cd3-8ce5-060456a856b4","Text 3150fd93-12fe-4675-a697-45c1db7facae","Text 9e729bce-1a7b-46e6-b9b5-e78fcaf41513","Text 9757dbfe-74ad-498a-a41e-4edafd403c8f"],
            "Seller2":["Text 8a3ef30d-601a-4f71-b108-af4041d67b7b","Text 8b3e05be-85a4-47b0-96ce-c95ed88aab4e","Text eb611128-2a6f-48c4-a4a9-8558b6e5af45"],
            "Day":["Text efd6729e-653d-4dc5-9eb5-6ba2b4afce7c",],
            "Year":["Text 2e813665-22d3-4bdc-bcaa-7b505dd567d5"],
            "Apn":["Text 33976459-a290-4365-8bcc-52b6132ea716",],
            "LegalDescription":["Text d4b9e8b5-9b87-4e07-a618-12bcc3d61ca9"],
            "Debt":["Text 72492c39-9afa-4008-bd82-75ff96a393c1","Text a829029c-a0b5-4f14-a891-1893793b6a1e","Text b0aefea7-7f48-4a17-b882-123b95ffc445"],
            "Phone":["Text d6a58bbd-a825-4b73-acb2-75c78fcf5b44"],
            "Broker":["Text 5498e23f-a693-4f95-87c7-15668099b82b"]},
        
    }

    bonusOffer={
        "fullNameTabs":{"FullName":["Name 654afd7a-cebc-41e3-adaa-ca2a135f9227"]},
        "textTabs":{
            "propertyAddress":["Text f4fea6fc-73af-42cb-9dca-a3a89278433b", "Text 96b302b1-eac1-4494-b6a7-6e60841fbd45"],
            "FullName":[],
            "Seler1":["Text 04c8164c-e4a8-44c9-8551-edd5b50b4757","Text 2ecb670f-53f1-4c5c-88f3-2d300aaf18df","Text 96595125-399d-4f15-8a22-9f250217a58c"],
            "Seller2":["Text 1d6719de-7739-4d80-9d6f-d85a464c0ac9"],
            "Day":[],
            "Year":[],
            "Apn":[],
            "LegalDescription":["Text 44d99d8d-5d3b-4cb3-b430-0d755728ac48"],
            "Debt":[""],
            "Phone":[],
            "Broker":[],
            "ClientEmail":[],
            "Address":[],
            "Apn":["Text e53e1a35-855e-4562-914f-8414f3516a7d"]

        }
    }
    envelope_data.emailSubject=envelope_data.emailSubject+" -OFFER-"
    day=validDay(datetime.now().strftime("%Y-%m-%d"))
    print("the date is",day)
    day=day.split(" ")
    envelope_data.Day=day[0]+" "+day[1] +","
    envelope_data.Year=day[0][2:]
    envelope_data.Seller1=envelope_data.Seller1First+" "+envelope_data.Seller1Last
    envelope_data.Seller2=envelope_data.Seller2First+" "+envelope_data.Seller2Last
    envelope_data.FullName=envelope_data.FirstName+" "+envelope_data.LastName
    tabs={}
    lableNames=TexasPurchaseContract
    if envelope_data.templateName=="Cash Offers-(Bonus Offers)":
        lableNames=bonusOffer

    for tab in lableNames.keys():
        for field in lableNames[tab].keys():
            if getattr(envelope_data,field,None)!=None:
                if tab not in tabs:
                    tabs[tab]=[]
                for tabLabel in lableNames[tab][field]:
                    value = getattr(envelope_data, field, "")
                    tabs[tab].append({
                        "tabLabel": tabLabel,
                        "value": value if value != "null" and value != "null null" else ""
                    })
    envelope = {
        "emailSubject": envelope_data.emailSubject,
        "status": "created",
        "compositeTemplates": [
            {
                "serverTemplates": [
                    {
                        "sequence": "1",
                        "templateId": templateId
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
                                    "tabs":tabs
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    print(envelope)
    
    response = requests.post(f"{baseURL}/{accountID}/envelopes",headers=headers,json=envelope)
    return response.json()


@app.get("/templates")
def templates():
    access_token = generateAccessToken()
    accountID = "d793357d-2249-42c3-a21a-e99f0a993bd7"
    templates = getTemplates(access_token,accountID)
    return templates

@app.post("/envelopeCompleted")
async def envelopeCompleted(envelope_data:DocusignHook):
    if envelope_data.event!="recipient-completed":
        return {"message":"Event not supported"}
    tag=envelope_data.data["envelopeSummary"]["customFields"]["textCustomFields"][2]["value"]+"Signed"
    contactId=envelope_data.data["envelopeSummary"]["customFields"]["textCustomFields"][1]["value"]
    accessToken="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2NhdGlvbl9pZCI6InVwZHczSWR3dnFlWkplZkM3blpnIiwiY29tcGFueV9pZCI6IjdOeFBlM3dlQk4wbnFQUjRDb2JWIiwidmVyc2lvbiI6MSwiaWF0IjoxNzA0OTk1Mzk5MTU1LCJzdWIiOiJ1c2VyX2lkIn0.WSaPvxAvNlzmJtZXCRgMvTTIrgOEl0p-GJOkF8kMk6Y"
    
    response=addTag(contactId,tag,accessToken)
    return response

@app.get("/tabs")
def getTabs():
    accountID = "d793357d-2249-42c3-a21a-e99f0a993bd7"
    access_token = generateAccessToken()
    template = getTemplate("Cash Offers-(Bonus Offers)", access_token,accountID)
    documents=requests.get(f"https://na4.docusign.net/restapi/v2.1/accounts/{accountID}/templates/{template['templateId']}/documents",headers={"Authorization": f"Bearer {access_token}"}).json()
    allTabs=[]
    for document in documents["templateDocuments"]:
        tabs = getDocumentTabs(document["documentId"], access_token, template["templateId"],accountID)
        allTabs.append(tabs)
    return allTabs
   
