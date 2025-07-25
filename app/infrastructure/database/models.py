from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute
from app.core.config import settings

class Property(Model):
    """
    Represents the Property item in the DynamoDB table.
    """
    class Meta:
        table_name = settings.DYNAMODB_PREFIX + "_properties"
        region = settings.DYNAMODB_REGION

        # If you're running locally and not using IAM roles, PynamoDB needs credentials.
        # These will be None if not set in the environment, and PynamoDB will
        # fall back to its default credential discovery process (e.g., IAM roles).

        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    id = UnicodeAttribute(range_key=True)
    customerid = UnicodeAttribute(hash_key=True)
    reicb_url = UnicodeAttribute(null=True)
    cash_to_seller = NumberAttribute(null=True)
    seller_carry_terms = UnicodeAttribute(null=True)
    agent_commission = NumberAttribute(null=True)
    debt = NumberAttribute(null=True)
    contract_price = NumberAttribute(null=True)
    
class Connection(Model):
    """
    Represents the REICB/GHL Connection item in the DynamoDB table.
    """
    class Meta:
        table_name = settings.DYNAMODB_PREFIX + "_connections"
        region = settings.DYNAMODB_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    locationid = UnicodeAttribute(hash_key=True)
    token = UnicodeAttribute()
    refresh = UnicodeAttribute()
    expires = UnicodeAttribute()
    locationname = UnicodeAttribute()
    code = UnicodeAttribute(null=True)