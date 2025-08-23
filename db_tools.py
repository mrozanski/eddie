import asyncio
import asyncpg
import os
import logging
from typing import List, Dict, Any, Optional
from fuzzywuzzy import fuzz
from langchain_core.tools import tool
import json

# Set up logging
logger = logging.getLogger(__name__)

class GuitarRegistryDB:
    """Database interface for Guitar Registry PostgreSQL database"""
    
    def __init__(self, connection_string: str):
        """
        Initialize database connection.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.pool = None
        self._connection_timeout = int(os.getenv('DB_CONNECTION_TIMEOUT', '5'))
        
    async def connect(self):
        """Establish database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=self._connection_timeout
            )
            logger.info("Database connection pool established")
        except Exception as e:
            logger.error(f"Failed to establish database connection: {e}")
            raise
    
    async def get_manufacturers(self) -> List[Dict[str, Any]]:
        """
        Retrieve all manufacturers from the manufacturers table.
        
        Returns:
            List of manufacturer dictionaries with id, name, country, etc.
        """
        if not self.pool:
            raise Exception("Database connection not established. Call connect() first.")
        
        try:
            async with self.pool.acquire() as connection:
                # Check if manufacturers table exists first
                table_check_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'manufacturers'
                );
                """
                table_exists = await connection.fetchval(table_check_query)
                
                if not table_exists:
                    logger.warning("Table 'manufacturers' does not exist. Please run the database schema to create the database tables.")
                    return []
                
                # Get all manufacturers from manufacturers table
                query = """
                SELECT id, name, country, founded_year, website, status, notes,
                       created_at, updated_at
                FROM manufacturers 
                WHERE status = 'active' OR status IS NULL
                ORDER BY name
                """
                rows = await connection.fetch(query)
                
                manufacturers = []
                for row in rows:
                    manufacturers.append({
                        'id': str(row['id']),
                        'name': row['name'],
                        'country': row['country'],
                        'founded_year': row['founded_year'],
                        'website': row['website'],
                        'status': row['status'],
                        'notes': row['notes'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    })
                
                logger.info(f"Retrieved {len(manufacturers)} manufacturers from database")
                return manufacturers
                
        except Exception as e:
            logger.error(f"Error retrieving manufacturers: {e}")
            return []
    
    async def find_manufacturer_matches(self, query: str, threshold: int = 70) -> List[Dict[str, Any]]:
        """
        Search for similar manufacturer names using fuzzy matching.
        
        Args:
            query: Search query for manufacturer name
            threshold: Minimum similarity score (0-100)
            
        Returns:
            List of similar manufacturer names with confidence scores
        """
        manufacturers = await self.get_manufacturers()
        matches = []
        
        for manufacturer in manufacturers:
            # Calculate fuzzy match score
            similarity = fuzz.ratio(query.lower(), manufacturer['name'].lower())
            partial_similarity = fuzz.partial_ratio(query.lower(), manufacturer['name'].lower())
            token_similarity = fuzz.token_sort_ratio(query.lower(), manufacturer['name'].lower())
            
            # Use the highest similarity score
            best_score = max(similarity, partial_similarity, token_similarity)
            
            if best_score >= threshold:
                matches.append({
                    'id': manufacturer['id'],
                    'name': manufacturer['name'],
                    'score': best_score,
                    'country': manufacturer['country'],
                    'founded_year': manufacturer['founded_year'],
                    'status': manufacturer['status']
                })
        
        # Sort by score descending
        matches.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Found {len(matches)} matches for query '{query}'")
        
        return matches
    
    async def normalize_manufacturer_name(self, input_name: str) -> str:
        """
        Return standardized manufacturer name from variations.
        
        Args:
            input_name: Raw manufacturer name from research
            
        Returns:
            Standardized manufacturer name or original if no match found
        """
        matches = await self.find_manufacturer_matches(input_name, threshold=85)
        
        if matches:
            # Return the best match
            normalized_name = matches[0]['name']
            logger.info(f"Normalized '{input_name}' to '{normalized_name}' (score: {matches[0]['score']})")
            return normalized_name
        else:
            logger.info(f"No normalization found for '{input_name}', returning original")
            return input_name
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

# Global database instance
_db_instance: Optional[GuitarRegistryDB] = None

def get_db_instance() -> Optional[GuitarRegistryDB]:
    """Get the global database instance"""
    return _db_instance

def set_db_instance(db: GuitarRegistryDB):
    """Set the global database instance"""
    global _db_instance
    _db_instance = db

@tool
async def manufacturer_lookup_tool(manufacturer_name: str) -> str:
    """
    Normalize manufacturer names using database lookup.
    
    Args:
        manufacturer_name: Raw manufacturer name from research
        
    Returns:
        Standardized manufacturer name
    """
    db = get_db_instance()
    if not db:
        logger.warning("Database not available for manufacturer lookup")
        return manufacturer_name
    
    try:
        normalized_name = await db.normalize_manufacturer_name(manufacturer_name)
        return f"Normalized manufacturer name: {normalized_name}"
    except Exception as e:
        logger.error(f"Error in manufacturer lookup: {e}")
        return f"Error normalizing '{manufacturer_name}': {str(e)}"

@tool
async def manufacturer_search_tool(query: str) -> str:
    """
    Find similar manufacturer names for fuzzy matching.
    
    Args:
        query: Search query for manufacturer names
        
    Returns:
        JSON string with list of similar manufacturer names with confidence scores
    """
    db = get_db_instance()
    if not db:
        logger.warning("Database not available for manufacturer search")
        return json.dumps({"error": "Database not available"})
    
    try:
        matches = await db.find_manufacturer_matches(query)
        
        # Format results for tool output
        results = {
            "query": query,
            "matches": [
                {
                    "name": match['name'],
                    "confidence": match['score'],
                    "country": match['country'],
                    "founded_year": match['founded_year'],
                    "status": match['status']
                }
                for match in matches[:5]  # Limit to top 5 matches
            ]
        }
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        logger.error(f"Error in manufacturer search: {e}")
        return json.dumps({"error": f"Search failed: {str(e)}"})

# Database configuration management
class DatabaseConfig:
    """Manages database configuration from environment and config files"""
    
    @staticmethod
    def get_connection_string() -> str:
        """
        Get database connection string from environment variables or config.
        
        Returns:
            PostgreSQL connection string
        """
        # Try environment variable first
        db_url = os.getenv('GUITAR_REGISTRY_DB_URL')
        if db_url:
            return db_url
        
        # Fallback to individual environment variables
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'guitar_registry')
        username = os.getenv('DB_USERNAME', 'username')
        password = os.getenv('DB_PASSWORD', 'password')
        
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if database integration is enabled"""
        return os.getenv('ENABLE_DB_TOOLS', 'true').lower() == 'true'

async def initialize_database() -> Optional[GuitarRegistryDB]:
    """
    Initialize database connection if enabled.
    
    Returns:
        GuitarRegistryDB instance or None if disabled/failed
    """
    if not DatabaseConfig.is_enabled():
        logger.info("Database integration disabled via ENABLE_DB_TOOLS")
        return None
    
    try:
        connection_string = DatabaseConfig.get_connection_string()
        
        # Check if connection string has placeholder values
        if 'username:password' in connection_string or 'localhost:5432/guitar_registry' in connection_string:
            logger.warning("Database connection string contains placeholder values. Please configure actual database credentials in .env file.")
            logger.info("To set up the database:")
            logger.info("1. Create a PostgreSQL database named 'guitar_registry'")
            logger.info("2. Ensure the manufacturers table exists in the database")
            logger.info("3. Update .env file with actual database credentials")
            return None
        
        db = GuitarRegistryDB(connection_string)
        await db.connect()
        set_db_instance(db)
        logger.info("Database integration initialized successfully")
        return db
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.info("Make sure:")
        logger.info("1. PostgreSQL is running and accessible")
        logger.info("2. Database 'guitar_registry' exists")
        logger.info("3. Database credentials are correct in .env file")
        logger.info("4. Database schema exists with manufacturers table")
        return None

async def cleanup_database():
    """Clean up database connections"""
    db = get_db_instance()
    if db:
        await db.close()
        set_db_instance(None)
        logger.info("Database connections cleaned up")