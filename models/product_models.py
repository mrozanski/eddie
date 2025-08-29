from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal


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


# Guitar Registry JSON Output Schema
class GuitarRegistryManufacturer(BaseModel):
    """Manufacturer information for guitar registry"""
    name: str = Field(description="Manufacturer name (1-100 characters)", min_length=1, max_length=100)
    country: Optional[str] = Field(None, description="Country of origin")
    founded_year: Optional[int] = Field(None, description="Year founded")
    website: Optional[str] = Field(None, description="Official website URL")
    status: Optional[str] = Field(None, description="Current status (active, inactive, etc.)")
    notes: Optional[str] = Field(None, description="Additional notes about manufacturer")


class GuitarRegistryModel(BaseModel):
    """Guitar model information for guitar registry"""
    manufacturer_name: str = Field(description="Manufacturer name matching existing manufacturer")
    name: str = Field(description="Model name (1-150 characters)", min_length=1, max_length=150)
    year: int = Field(description="Model year (1900-2030)", ge=1900, le=2030)
    body_type: Optional[str] = Field(None, description="Body type (solid, hollow, semi-hollow)")
    wood_body: Optional[str] = Field(None, description="Body wood material")
    wood_neck: Optional[str] = Field(None, description="Neck wood material")
    wood_fretboard: Optional[str] = Field(None, description="Fretboard wood material")
    pickup_configuration: Optional[str] = Field(None, description="Pickup configuration (HH, SSS, HSS, etc.)")
    scale_length: Optional[float] = Field(None, description="Scale length in inches")
    frets: Optional[int] = Field(None, description="Number of frets")
    notes: Optional[str] = Field(None, description="Additional notes about the model")


class GuitarRegistryModelReference(BaseModel):
    """Complete model reference for individual guitar identification"""
    manufacturer_name: str = Field(description="Manufacturer name")
    model_name: str = Field(description="Model name")
    year: int = Field(description="Model year")


class GuitarRegistryIndividualGuitar(BaseModel):
    """Individual guitar information for guitar registry"""
    # Option A: Complete Model Reference (preferred)
    model_reference: Optional[GuitarRegistryModelReference] = Field(None, description="Complete model reference")
    
    # Option B: Fallback Manufacturer + Model
    manufacturer_name_fallback: Optional[str] = Field(None, description="Fallback manufacturer name")
    model_name_fallback: Optional[str] = Field(None, description="Fallback model name")
    
    # Option C: Fallback Manufacturer + Description
    description: Optional[str] = Field(None, description="Guitar description when model not available")
    
    # Additional guitar details
    serial_number: Optional[str] = Field(None, description="Serial number")
    color: Optional[str] = Field(None, description="Guitar color/finish")
    condition: Optional[str] = Field(None, description="Condition (mint, excellent, good, fair, poor)")
    price: Optional[float] = Field(None, description="Price in USD")
    currency: Optional[str] = Field("USD", description="Currency code")
    date_manufactured: Optional[str] = Field(None, description="Manufacturing date (YYYY-MM-DD)")
    date_listed: Optional[str] = Field(None, description="Listing date (YYYY-MM-DD)")
    location: Optional[str] = Field(None, description="Location where guitar is available")
    notes: Optional[str] = Field(None, description="Additional notes about this specific guitar")


class GuitarRegistrySourceAttribution(BaseModel):
    """Source attribution for guitar registry"""
    source_name: str = Field(description="Source name (1-100 characters)", min_length=1, max_length=100)
    url: Optional[str] = Field(None, description="Source URL")
    date_accessed: Optional[str] = Field(None, description="Date accessed (YYYY-MM-DD)")
    reliability: Optional[str] = Field(None, description="Source reliability assessment")
    notes: Optional[str] = Field(None, description="Additional notes about the source")


class GuitarRegistryOutput(BaseModel):
    """Complete guitar registry JSON output schema"""
    manufacturer: GuitarRegistryManufacturer = Field(description="Manufacturer information")
    model: GuitarRegistryModel = Field(description="Guitar model information")
    individual_guitar: GuitarRegistryIndividualGuitar = Field(description="Individual guitar information")
    source_attribution: GuitarRegistrySourceAttribution = Field(description="Source attribution information")
