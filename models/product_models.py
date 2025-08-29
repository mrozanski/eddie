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


# Guitar Registry JSON Output Schema - Updated to match guitar processor requirements
class GuitarRegistryManufacturer(BaseModel):
    """Manufacturer information for guitar registry"""
    name: str = Field(description="Manufacturer name (1-100 characters)", min_length=1, max_length=100)
    country: Optional[str] = Field(None, description="Country of origin", max_length=50)
    founded_year: Optional[int] = Field(None, description="Year founded (1800-2030)", ge=1800, le=2030)
    website: Optional[str] = Field(None, description="Official website URL")
    status: Optional[str] = Field("active", description="Current status (active, defunct, acquired)")
    notes: Optional[str] = Field(None, description="Additional notes about manufacturer")
    logo_source: Optional[str] = Field(None, description="Path to company logo image file")


class GuitarRegistrySpecifications(BaseModel):
    """Technical specifications for guitar model"""
    body_type: Optional[str] = Field(None, description="Body type (solid, hollow, semi-hollow)")
    wood_body: Optional[str] = Field(None, description="Body wood material")
    wood_neck: Optional[str] = Field(None, description="Neck wood material")
    wood_fretboard: Optional[str] = Field(None, description="Fretboard wood material")
    pickup_configuration: Optional[str] = Field(None, description="Pickup configuration (HH, SSS, HSS, etc.)")
    scale_length: Optional[float] = Field(None, description="Scale length in inches")
    frets: Optional[int] = Field(None, description="Number of frets")


class GuitarRegistryFinish(BaseModel):
    """Finish information for guitar model"""
    finish_name: Optional[str] = Field(None, description="Name of the finish")
    finish_type: Optional[str] = Field(None, description="Type of finish (nitrocellulose, polyurethane, etc.)")
    rarity: Optional[str] = Field(None, description="Rarity of the finish")


class GuitarRegistryModel(BaseModel):
    """Guitar model information for guitar registry - Updated to match schema"""
    manufacturer_name: str = Field(description="Manufacturer name matching existing manufacturer")
    name: str = Field(description="Model name (1-150 characters)", min_length=1, max_length=150)
    year: int = Field(description="Model year (1900-2030)", ge=1900, le=2030)
    
    # Optional fields from guitar processor schema
    product_line_name: Optional[str] = Field(None, description="Product series or line name")
    production_type: Optional[str] = Field("mass", description="Production type")
    production_start_date: Optional[str] = Field(None, description="Production start date (YYYY-MM-DD)")
    production_end_date: Optional[str] = Field(None, description="Production end date (YYYY-MM-DD)")
    estimated_production_quantity: Optional[int] = Field(None, description="Estimated production quantity", ge=1)
    msrp_original: Optional[float] = Field(None, description="Original retail price", ge=0)
    currency: Optional[str] = Field("USD", description="Currency code", max_length=3)
    description: Optional[str] = Field(None, description="Detailed description of the model")
    
    # Specifications and finishes as nested objects (required by schema)
    specifications: Optional[GuitarRegistrySpecifications] = Field(None, description="Technical specifications")
    finishes: Optional[List[GuitarRegistryFinish]] = Field(None, description="Available finishes")


class GuitarRegistryModelReference(BaseModel):
    """Complete model reference for individual guitar identification"""
    manufacturer_name: str = Field(description="Manufacturer name")
    model_name: str = Field(description="Model name")
    year: int = Field(description="Model year")


class GuitarRegistryPhoto(BaseModel):
    """Photo information for guitar registry"""
    image_url: Optional[str] = Field(None, description="URL or path to the image")
    image_type: Optional[str] = Field(None, description="Type of image (primary, gallery, detail, etc.)")
    caption: Optional[str] = Field(None, description="Image caption or description")
    source: Optional[str] = Field(None, description="Source of the image")
    date_taken: Optional[str] = Field(None, description="Date when photo was taken (YYYY-MM-DD)")


class GuitarRegistryIndividualGuitar(BaseModel):
    """Individual guitar information for guitar registry - Updated to match schema"""
    # Option A: Complete Model Reference (preferred)
    model_reference: Optional[GuitarRegistryModelReference] = Field(None, description="Complete model reference")
    
    # Option B: Fallback Manufacturer + Model
    manufacturer_name_fallback: Optional[str] = Field(None, description="Fallback manufacturer name", max_length=100)
    model_name_fallback: Optional[str] = Field(None, description="Fallback model name", max_length=150)
    
    # Option C: Fallback Manufacturer + Description
    description: Optional[str] = Field(None, description="Guitar description when model not available")
    
    # Additional guitar details from guitar processor schema
    year_estimate: Optional[str] = Field(None, description="Year estimate (e.g., 'circa 1959', 'late 1950s')", max_length=50)
    serial_number: Optional[str] = Field(None, description="Serial number", max_length=50)
    production_date: Optional[str] = Field(None, description="Production date (YYYY-MM-DD)")
    production_number: Optional[int] = Field(None, description="Production sequence number")
    significance_level: Optional[str] = Field("notable", description="Significance level")
    significance_notes: Optional[str] = Field(None, description="Explanation of significance")
    current_estimated_value: Optional[float] = Field(None, description="Current market value estimate")
    last_valuation_date: Optional[str] = Field(None, description="Date of last valuation (YYYY-MM-DD)")
    condition_rating: Optional[str] = Field(None, description="Condition rating")
    modifications: Optional[str] = Field(None, description="Description of modifications")
    provenance_notes: Optional[str] = Field(None, description="History of ownership and usage")
    
    # Legacy fields for backward compatibility
    color: Optional[str] = Field(None, description="Guitar color/finish")
    condition: Optional[str] = Field(None, description="Condition (mint, excellent, good, fair, poor)")
    price: Optional[float] = Field(None, description="Price in USD")
    currency: Optional[str] = Field("USD", description="Currency code")
    date_manufactured: Optional[str] = Field(None, description="Manufacturing date (YYYY-MM-DD)")
    date_listed: Optional[str] = Field(None, description="Listing date (YYYY-MM-DD)")
    location: Optional[str] = Field(None, description="Location where guitar is available")
    notes: Optional[str] = Field(None, description="Additional notes about this specific guitar")
    
    # Individual-specific specifications
    specifications: Optional[GuitarRegistrySpecifications] = Field(None, description="Individual-specific specifications")
    photos: Optional[List[GuitarRegistryPhoto]] = Field(None, description="Array of photo objects")


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
