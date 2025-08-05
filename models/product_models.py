from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class ProductSearchInput(BaseModel):
    manufacturer: str = Field(description="A guitar manufacturer name, e.g. Gibson")
    product_name: str = Field(description="A guitar product name, e.g. Les Paul Standard")
    year: str = Field(description="A guitar year, e.g. 2021")


class ProductToModelMapper:
    """
    Translation layer to map between product domain terminology and database model fields.
    This helps avoid confusion between 'product' (domain concept) and 'model' (database field).
    """
    
    @staticmethod
    def map_product_to_model(product: ProductSearchInput) -> Dict[str, Any]:
        """
        Convert ProductSearchInput to database model format.
        
        Args:
            product: ProductSearchInput object with product domain terminology
            
        Returns:
            Dictionary with database field names for API/database operations
        """
        return {
            "manufacturer": product.manufacturer,
            "model": product.product_name,  # translate product_name to model field
            "year": product.year
        }
    
    @staticmethod
    def map_model_to_product(model_data: Dict[str, Any]) -> ProductSearchInput:
        """
        Convert database model data to ProductSearchInput format.
        
        Args:
            model_data: Dictionary with database field names
            
        Returns:
            ProductSearchInput object with product domain terminology
        """
        return ProductSearchInput(
            manufacturer=model_data["manufacturer"],
            product_name=model_data["model"],  # translate model field to product_name
            year=model_data["year"]
        )
