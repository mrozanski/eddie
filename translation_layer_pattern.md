# Translation Layer Pattern for Domain Naming Conflicts

## Why This Pattern?

When building software systems, we often encounter naming conflicts between domain terminology and technical implementation details. A common example is the word "model" - it can refer to:
- **Domain concept**: A guitar model (e.g., "Les Paul Standard")
- **Technical concept**: A data model class, ML model, or design pattern

This creates confusion in codebases where both concepts coexist. The translation layer pattern provides a clean separation between domain language and technical implementation, making code more readable and maintainable.

## Implementation

### Domain Models (Clear Terminology)

```python
from pydantic import BaseModel, Field
from typing import Dict, Any

class ProductSearchInput(BaseModel):
    manufacturer: str = Field(description="A guitar manufacturer name, e.g. Gibson")
    product_name: str = Field(description="A guitar product name, e.g. Les Paul Standard")
    year: str = Field(description="A guitar year, e.g. 2021")
```

### Translation Layer

```python
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
```

## Usage Examples

### Example 1: Creating a product search input (domain terminology)

```python
from models.product_models import ProductSearchInput, ProductToModelMapper

# Create a search input using product domain terminology
product_search = ProductSearchInput(
    manufacturer="Gibson",
    product_name="Les Paul Standard",  # clear product terminology
    year="2021"
)

# Convert to database format for API calls
db_search_params = ProductToModelMapper.map_product_to_model(product_search)
print(db_search_params)
# Output: {'manufacturer': 'Gibson', 'model': 'Les Paul Standard', 'year': '2021'}
```

### Example 2: Converting database response back to product format

```python
# Simulate database response
db_response = {
    "manufacturer": "Fender",
    "model": "Stratocaster",  # database field name
    "year": "2020"
}

# Convert back to product domain terminology
product_data = ProductToModelMapper.map_model_to_product(db_response)
print(f"Product: {product_data.product_name} by {product_data.manufacturer}")
# Output: Product: Stratocaster by Fender
```

### Example 3: In a research agent workflow

```python
def search_guitar_products(manufacturer: str, product_name: str, year: str):
    # Use clear product terminology in your agent
    search_input = ProductSearchInput(
        manufacturer=manufacturer,
        product_name=product_name,  # much clearer than "model"
        year=year
    )
    
    # Convert for API call
    api_params = ProductToModelMapper.map_product_to_model(search_input)
    
    # Make API call with database field names
    # response = api_client.search_models(**api_params)
    
    # Convert response back to product terminology
    # return ProductToModelMapper.map_model_to_product(response)
```

## Benefits

1. **Clear Domain Language**: Use domain-appropriate terminology in business logic
2. **Database Compatibility**: Translation layer handles mapping to existing schema
3. **Maintainability**: Schema changes only require mapper updates
4. **Type Safety**: Pydantic models provide validation and IDE support
5. **Documentation**: Mapper clearly shows relationships between concepts
6. **Separation of Concerns**: Domain logic separate from technical implementation

## When to Apply This Pattern

- **Legacy Systems**: When you can't change existing database schemas
- **Naming Conflicts**: When domain terms conflict with technical terms
- **Multi-Layer Architecture**: When different layers use different terminology
- **API Design**: When internal and external APIs use different naming conventions
- **UI/UX**: When user-facing terminology differs from backend terminology

## Alternative Naming Strategies

If you can't use translation layers, consider:
- **Type Aliases**: `GuitarProduct = str`
- **Namespacing**: `guitar_catalog_models.py`
- **Contextual Naming**: `GuitarProductSearchInput`
- **Domain-Specific Terms**: `Ax`, `Rig`, `Gear` (music industry terms) 