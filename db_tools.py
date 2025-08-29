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
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

# Global database instance and manufacturer cache
_db_instance: Optional[GuitarRegistryDB] = None
_manufacturer_cache: Optional[List[Dict[str, Any]]] = None

def get_db_instance() -> Optional[GuitarRegistryDB]:
    """Get the global database instance"""
    return _db_instance

def set_db_instance(db: Optional[GuitarRegistryDB]):
    """Set the global database instance
    
    Args:
        db: GuitarRegistryDB instance or None to clear the global instance
    """
    global _db_instance
    _db_instance = db

def get_manufacturer_cache() -> Optional[List[Dict[str, Any]]]:
    """Get the cached manufacturer data"""
    return _manufacturer_cache

def set_manufacturer_cache(manufacturers: Optional[List[Dict[str, Any]]]):
    """Set the cached manufacturer data
    
    Args:
        manufacturers: List of manufacturer dictionaries or None to clear the cache
    """
    global _manufacturer_cache
    _manufacturer_cache = manufacturers

def _sync_manufacturer_lookup(manufacturer_name: str) -> str:
    """Synchronous version of manufacturer lookup for tools using cached data"""
    
    # First try to use cached data
    manufacturers = get_manufacturer_cache()
    if manufacturers:
        # Perform fuzzy matching on cached data
        matches = []
        
        for manufacturer in manufacturers:
            similarity = fuzz.ratio(manufacturer_name.lower(), manufacturer['name'].lower())
            partial_similarity = fuzz.partial_ratio(manufacturer_name.lower(), manufacturer['name'].lower())
            token_similarity = fuzz.token_sort_ratio(manufacturer_name.lower(), manufacturer['name'].lower())
            
            best_score = max(similarity, partial_similarity, token_similarity)
            
            if best_score >= 85:  # Use threshold of 85 for normalization
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
        
        if matches:
            normalized_name = matches[0]['name']
            logger.info(f"Normalized '{manufacturer_name}' to '{normalized_name}' via cache (score: {matches[0]['score']})")
            return normalized_name
    
    # Fallback to database if cache not available
    db = get_db_instance()
    if not db:
        logger.warning("Database not available for manufacturer lookup")
        return manufacturer_name
    
    try:
        # Create a completely isolated async execution context
        import concurrent.futures
        
        def run_async_lookup():
            """Run the async lookup in a completely isolated context"""
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Create a new database connection for this operation
                import asyncpg
                from db_tools import DatabaseConfig
                
                # Get connection string
                connection_string = DatabaseConfig.get_connection_string()
                
                async def isolated_lookup():
                    # Create a fresh connection for this operation
                    conn = await asyncpg.connect(connection_string)
                    try:
                        # Get manufacturers directly
                        rows = await conn.fetch("""
                            SELECT id, name, country, founded_year, website, status, notes
                            FROM manufacturers 
                            WHERE status = 'active' OR status IS NULL
                            ORDER BY name
                        """)
                        
                        manufacturers = [dict(row) for row in rows]
                        
                        # Perform fuzzy matching
                        matches = []
                        
                        for manufacturer in manufacturers:
                            similarity = fuzz.ratio(manufacturer_name.lower(), manufacturer['name'].lower())
                            partial_similarity = fuzz.partial_ratio(manufacturer_name.lower(), manufacturer['name'].lower())
                            token_similarity = fuzz.token_sort_ratio(manufacturer_name.lower(), manufacturer['name'].lower())
                            
                            best_score = max(similarity, partial_similarity, token_similarity)
                            
                            if best_score >= 85:  # Use threshold of 85 for normalization
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
                        
                        if matches:
                            return matches[0]['name']
                        else:
                            return manufacturer_name
                            
                    finally:
                        await conn.close()
                
                return loop.run_until_complete(isolated_lookup())
                
            finally:
                loop.close()
        
        # Execute in a separate thread to avoid any event loop conflicts
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_async_lookup)
            normalized_name = future.result(timeout=15)
        
        return normalized_name
        
    except Exception as e:
        logger.error(f"Error in manufacturer lookup: {e}")
        # Fallback to original name if database lookup fails
        return manufacturer_name

@tool
def manufacturer_lookup_tool(manufacturer_name: str) -> str:
    """
    Normalize manufacturer names using database lookup.
    
    Args:
        manufacturer_name: Raw manufacturer name from research
        
    Returns:
        Standardized manufacturer name
    """
    try:
        normalized_name = _sync_manufacturer_lookup(manufacturer_name)
        return f"Normalized manufacturer name: {normalized_name}"
    except Exception as e:
        logger.error(f"Error in manufacturer lookup: {e}")
        return f"Error normalizing '{manufacturer_name}': {str(e)}"

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
        if 'username:password' in connection_string:
            logger.warning("Database connection string contains placeholder values. Please configure actual database credentials in .env file.")
            logger.info("To set up the database:")
            logger.info("1. Create a PostgreSQL database named 'guitar_registry'")
            logger.info("2. Ensure the manufacturers table exists in the database")
            logger.info("3. Update .env file with actual database credentials")
            return None
        
        db = GuitarRegistryDB(connection_string)
        await db.connect()
        set_db_instance(db)
        
        # Pre-load manufacturers into cache for batch processing
        try:
            manufacturers = await db.get_manufacturers()
            set_manufacturer_cache(manufacturers)
            logger.info(f"Pre-loaded {len(manufacturers)} manufacturers into cache for batch processing")
        except Exception as e:
            logger.warning(f"Could not pre-load manufacturers into cache: {e}")
        
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
        set_manufacturer_cache(None)  # Clear cache
        logger.info("Database connections and cache cleaned up")
