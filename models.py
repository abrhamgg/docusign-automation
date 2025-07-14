# models.py
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    MapAttribute,
    ListAttribute
)
from dotenv import load_dotenv
import os
load_dotenv()


class PropertyAddressParts(MapAttribute):
    property_street = UnicodeAttribute(null=True)
    property_city = UnicodeAttribute(null=True)
    property_state = UnicodeAttribute(null=True)
    property_zip = UnicodeAttribute(null=True)

class LegalDescriptionParts(MapAttribute):
    lot = UnicodeAttribute(null=True)
    blk = UnicodeAttribute(null=True)
    subdivision = UnicodeAttribute(null=True)
    section = UnicodeAttribute(null=True)

class Verification(MapAttribute):
    name = UnicodeAttribute(null=True)
    ownership = NumberAttribute(null=True)

class Metadata(MapAttribute):
    target = UnicodeAttribute(null=True)

class Phone(MapAttribute):
    phone = UnicodeAttribute()
    type = UnicodeAttribute(null=True)
    verification = Verification(null=True)
    metadata = Metadata(null=True)

class TenantDataRecord(Model):
    """
    DynamoDB Table: TenantDataRecords
    """
    class Meta:
        table_name = "craimer_countystream"
        region = ("us-east-2")

    tenant_id = UnicodeAttribute(hash_key=True)
    timestamp = UnicodeAttribute(range_key=True)

    # Top-level attributes
    lead_id = UnicodeAttribute(null=True)
    notice_id = NumberAttribute(null=True)
    instrument_number = UnicodeAttribute(null=True)
    property_address = UnicodeAttribute(null=True)
    auction_datetime = UnicodeAttribute(null=True)
    auction_location = UnicodeAttribute(null=True)
    principal_balance = NumberAttribute(null=True)
    lender = UnicodeAttribute(null=True)
    original_lender = UnicodeAttribute(null=True)
    law_firm = UnicodeAttribute(null=True)
    law_firm_phone = UnicodeAttribute(null=True)
    grantor_1 = UnicodeAttribute(null=True)
    grantor_2 = UnicodeAttribute(null=True)
    property_city = UnicodeAttribute(null=True)
    property_state = UnicodeAttribute(null=True)
    property_zip = UnicodeAttribute(null=True)
    legal_description = UnicodeAttribute(null=True)

    # Nested
    property_address_parts = PropertyAddressParts(null=True)
    legal_description_parts = LegalDescriptionParts(null=True)
    phones = ListAttribute(of=Phone, null=True)

    @classmethod
    def create_record(cls, tenant_id, timestamp, data: dict):
        """
        Create a record in DynamoDB.
        """
        record = cls(
            tenant_id=tenant_id,
            timestamp=timestamp,
            lead_id=data.get("lead_id"),
            notice_id=data.get("Notice_id"),
            instrument_number=data.get("instrument_number"),
            property_address=data.get("property_address"),
            auction_datetime=data.get("auction_datetime"),
            auction_location=data.get("auction_location"),
            principal_balance=data.get("principal_balance"),
            lender=data.get("lender"),
            original_lender=data.get("original_lender"),
            law_firm=data.get("law_firm"),
            law_firm_phone=data.get("law_firm_phone"),
            grantor_1=data.get("grantor_1"),
            grantor_2=data.get("grantor_2"),
            property_city=data.get("property_address_parts", {}).get("property_city"),
            property_state=data.get("property_address_parts", {}).get("property_state"),
            property_zip=data.get("property_address_parts", {}).get("property_zip"),
            legal_description=data.get("legal_description"),
            property_address_parts=data.get("property_address_parts"),
            legal_description_parts=data.get("legal_description_parts"),
            phones=data.get("phones")
        )
        record.save()
        return record

    @classmethod
    def query_by_tenant(cls, tenant_id):
        """
        Get all records for a tenant.
        """
        return cls.query(tenant_id)

    @classmethod
    def get_record(cls, tenant_id, timestamp):
        """
        Retrieve a single record by tenant_id and timestamp.
        """
        return cls.get(tenant_id, timestamp)
