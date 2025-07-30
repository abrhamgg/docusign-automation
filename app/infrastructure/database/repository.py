from pynamodb.exceptions import DoesNotExist
from app.infrastructure.database.models import Connection, Property

class PropertyRepository:
    """
    Handles data operations for Property items in DynamoDB.
    """

    def get_property_by_id(self, customer_id: str, property_id: str) -> dict | None:
        """
        Retrieves a single property from the database using its composite primary key.

        Args:
            customer_id: The hash key for the property item.
            property_id: The range key for the property item.

        Returns:
            A dictionary containing the property data if found, otherwise None.
        """
        try:
            # Use the .get() method to fetch the item with the full primary key.
            # This is the most efficient way to read a single item in DynamoDB.
            property_item = Property.get(customer_id, property_id)
            
            # Return the model's attributes as a dictionary.
            # This ensures the service layer receives plain data, not a PynamoDB object.
            return property_item.attribute_values

        except DoesNotExist:
            # If the item doesn't exist, PynamoDB raises this exception.
            return None
        except Exception as e:
            # In a real-world scenario, you would add structured logging here.
            print(f"An error occurred while fetching property {property_id} for customer {customer_id}: {e}")
            # Re-raise or handle as appropriate for your application's error strategy.
            raise

class ConnectionRepository:
    """
    Handles data operations for Connection items in DynamoDB.
    """
    def get_connection(self, location_id: str) -> Connection | None:
        """Retrieves a connection by its location ID."""
        try:
            return Connection.get(location_id)
        except DoesNotExist:
            return None
        except Exception as e:
            print(f"Error getting connection for location '{location_id}': {e}")
            raise

    def save_connection(self, connection: Connection):
        """Saves a Connection object to the database."""
        try:
            connection.save()
        except Exception as e:
            print(f"Error saving connection for location '{connection.locationid}': {e}")
            raise

    


