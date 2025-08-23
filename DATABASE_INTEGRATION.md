# Database Integration for Guitar Registry ProductSearchAgent

This document describes the database integration feature that enhances the ProductSearchAgent with PostgreSQL connectivity for manufacturer name normalization and fuzzy matching capabilities.

## Features

### 🎯 Manufacturer Name Normalization
- Automatically standardizes manufacturer names using existing database data
- Converts variations like "Gibson Corp", "Gibson Corporation" to "Gibson"
- Improves data consistency across research sessions

### 🔍 Fuzzy Matching
- Finds similar manufacturer names when exact matches aren't found
- Uses advanced fuzzy matching algorithms (Levenshtein distance, partial matches, token sorting)
- Configurable similarity thresholds

### 🛡️ Graceful Degradation
- Agent continues to work normally if database is unavailable
- No breaking changes to existing functionality
- Error handling and logging for database issues

## Setup

### 1. Install Dependencies

The required dependencies are already included in `pyproject.toml`:
- `asyncpg` - PostgreSQL async driver
- `fuzzywuzzy[speedup]` - Fuzzy string matching

Install with:
```bash
pip install -e .
```

### 2. Database Configuration

#### Option A: Environment Variables (Recommended)
Create a `.env` file based on `.env.example`:

```bash
# Database Configuration
GUITAR_REGISTRY_DB_URL=postgresql://username:password@localhost:5432/guitar_registry

# Database Settings
DB_CONNECTION_TIMEOUT=5
ENABLE_DB_TOOLS=true
```

#### Option B: Individual Environment Variables
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=guitar_registry
DB_USERNAME=username
DB_PASSWORD=password
```

#### Option C: Configuration File
Update `config/database_config.json` with your database credentials.

### 3. Database Schema

The integration expects a table with manufacturer information. Example schema:

```sql
CREATE TABLE guitars (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(255),
    model VARCHAR(255),
    year INTEGER,
    -- other columns...
);

-- Index for better performance
CREATE INDEX idx_guitars_manufacturer ON guitars(manufacturer);
```

## Usage

### Basic Usage with Database Integration

```python
from product_search_agent import ProductSearchAgent
from models.product_models import ProductSearchInput

# Create input
input_data = ProductSearchInput(
    manufacturer="Gibson Corp",  # Will be normalized to "Gibson"
    product_name="Les Paul Standard",
    year="2020"
)

# Create agent with database integration (default: enabled)
agent = ProductSearchAgent(input=input_data)
await agent.setup()

# Run search
messages = await agent.run_superstep(message="")
for m in messages['messages']:
    m.pretty_print()

# Clean up
agent.cleanup()
```

### Disable Database Integration

```python
# Create agent without database integration
agent = ProductSearchAgent(input=input_data, enable_db=False)
```

### Direct Database Tool Usage

```python
from db_tools import manufacturer_lookup_tool, manufacturer_search_tool

# Normalize manufacturer name
result = await manufacturer_lookup_tool.ainvoke({
    "manufacturer_name": "Gibson Corporation"
})
# Returns: "Normalized manufacturer name: Gibson"

# Search for similar manufacturers
result = await manufacturer_search_tool.ainvoke({
    "query": "Gib"
})
# Returns JSON with matching manufacturers and confidence scores
```

## Available Tools

The database integration adds two new tools to the ProductSearchAgent:

### 1. `manufacturer_lookup_tool`
- **Purpose**: Normalize manufacturer names using database lookup
- **Input**: Raw manufacturer name from research
- **Output**: Standardized manufacturer name
- **Usage**: Agent calls this automatically when finding manufacturer information

### 2. `manufacturer_search_tool`
- **Purpose**: Find similar manufacturer names using fuzzy matching
- **Input**: Search query
- **Output**: JSON list of similar manufacturers with confidence scores
- **Usage**: Agent uses this when manufacturer names are unclear or have variations

## Testing

Run the comprehensive test suite:

```bash
python test_db_integration.py
```

This tests:
- Direct database tool functionality
- Agent with database integration enabled
- Agent with database integration disabled
- Graceful degradation when database is unavailable

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GUITAR_REGISTRY_DB_URL` | - | Full PostgreSQL connection string |
| `ENABLE_DB_TOOLS` | `true` | Enable/disable database integration |
| `DB_CONNECTION_TIMEOUT` | `5` | Database query timeout in seconds |
| `DB_HOST` | `localhost` | Database host (fallback) |
| `DB_PORT` | `5432` | Database port (fallback) |
| `DB_NAME` | `guitar_registry` | Database name (fallback) |
| `DB_USERNAME` | `username` | Database username (fallback) |
| `DB_PASSWORD` | `password` | Database password (fallback) |

### Configuration File Settings

In `config/database_config.json`:

```json
{
  "features": {
    "enable_db_tools": true,
    "fuzzy_match_threshold": 70,
    "normalization_threshold": 85
  }
}
```

## Error Handling

The database integration includes comprehensive error handling:

- **Connection Failures**: Agent continues without database tools
- **Query Timeouts**: Configurable timeout with fallback behavior
- **Invalid Credentials**: Graceful error logging and degradation
- **Network Issues**: Retry logic and connection pooling

## Performance Considerations

- **Connection Pooling**: Async connection pool for concurrent requests
- **Query Optimization**: Indexed manufacturer lookups for fast searches
- **Caching**: Manufacturer data cached during agent lifecycle
- **Timeouts**: Configurable timeouts prevent hanging operations

## Backward Compatibility

- ✅ Existing code works without changes
- ✅ Database integration is optional (enabled by default)
- ✅ No breaking changes to existing API
- ✅ Fallback behavior when database unavailable

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check connection string and credentials
   - Verify database is running and accessible
   - Check firewall/network settings

2. **No Database Tools in Agent**
   - Verify `ENABLE_DB_TOOLS=true` in environment
   - Check for import errors in logs
   - Ensure database dependencies installed

3. **Poor Fuzzy Matching Results**
   - Adjust `fuzzy_match_threshold` in config
   - Check manufacturer data quality in database
   - Consider adding more manufacturer variations

### Debug Logging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Potential improvements for future versions:

- **Model/Product Normalization**: Extend beyond manufacturer names
- **Historical Data Integration**: Track research history in database
- **Machine Learning**: Learn from user corrections and feedback
- **Caching Layer**: Redis integration for performance
- **Analytics**: Track normalization accuracy and usage patterns