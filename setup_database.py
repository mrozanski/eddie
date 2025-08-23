#!/usr/bin/env python3
"""
Database setup script for Guitar Registry.

This script helps set up the database for testing the database integration feature.
It can create the database schema and insert sample data.

Usage:
    python setup_database.py --help
    python setup_database.py --check-connection
    python setup_database.py --create-schema
    python setup_database.py --insert-sample-data
    python setup_database.py --setup-all
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_connection():
    """Check if database connection is working"""
    print("🔍 Checking database connection...")
    
    # Try to get connection string
    db_url = os.getenv('GUITAR_REGISTRY_DB_URL')
    if not db_url:
        # Build from individual components
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'guitar_registry')
        username = os.getenv('DB_USERNAME', 'username')
        password = os.getenv('DB_PASSWORD', 'password')
        db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    if 'username:password' in db_url:
        print("❌ Database connection string contains placeholder values")
        print("   Please update your .env file with actual database credentials")
        return False
    
    try:
        conn = await asyncpg.connect(db_url)
        await conn.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Verify database 'guitar_registry' exists")
        print("3. Check credentials in .env file")
        return False

async def create_schema():
    """Create database schema from SQL file"""
    print("🏗️  Creating database schema...")
    
    schema_file = Path("database_schema.sql")
    if not schema_file.exists():
        print(f"❌ Schema file {schema_file} not found")
        return False
    
    db_url = os.getenv('GUITAR_REGISTRY_DB_URL')
    if not db_url:
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'guitar_registry')
        username = os.getenv('DB_USERNAME', 'username')
        password = os.getenv('DB_PASSWORD', 'password')
        db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    try:
        # Read schema file
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema
        conn = await asyncpg.connect(db_url)
        await conn.execute(schema_sql)
        await conn.close()
        
        print("✅ Database schema created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create schema: {e}")
        return False

async def check_tables():
    """Check if required tables exist"""
    print("📋 Checking database tables...")
    
    db_url = os.getenv('GUITAR_REGISTRY_DB_URL')
    if not db_url:
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'guitar_registry')
        username = os.getenv('DB_USERNAME', 'username')
        password = os.getenv('DB_PASSWORD', 'password')
        db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    try:
        conn = await asyncpg.connect(db_url)
        
        # Check for guitars table
        guitars_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'guitars'
            );
        """)
        
        # Check for manufacturers table
        manufacturers_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'manufacturers'
            );
        """)
        
        # Count records
        guitar_count = 0
        manufacturer_count = 0
        
        if guitars_exists:
            guitar_count = await conn.fetchval("SELECT COUNT(*) FROM guitars")
            print(f"✅ 'guitars' table exists with {guitar_count} records")
        else:
            print("❌ 'guitars' table does not exist")
        
        if manufacturers_exists:
            manufacturer_count = await conn.fetchval("SELECT COUNT(*) FROM manufacturers")
            print(f"✅ 'manufacturers' table exists with {manufacturer_count} records")
        else:
            print("❌ 'manufacturers' table does not exist")
        
        await conn.close()
        
        return guitars_exists and manufacturers_exists
        
    except Exception as e:
        print(f"❌ Failed to check tables: {e}")
        return False

async def test_integration():
    """Test the database integration tools"""
    print("🧪 Testing database integration...")
    
    try:
        from db_tools import initialize_database, manufacturer_lookup_tool, manufacturer_search_tool
        
        # Initialize database
        db = await initialize_database()
        if not db:
            print("❌ Database integration initialization failed")
            return False
        
        # Test manufacturer lookup
        print("Testing manufacturer lookup...")
        result = await manufacturer_lookup_tool.ainvoke({"manufacturer_name": "Gibson Corp"})
        print(f"  Gibson Corp → {result}")
        
        # Test manufacturer search
        print("Testing manufacturer search...")
        result = await manufacturer_search_tool.ainvoke({"query": "Gib"})
        print(f"  Search 'Gib' → Found matches")
        
        # Cleanup
        from db_tools import cleanup_database
        await cleanup_database()
        
        print("✅ Database integration test successful")
        return True
        
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        return False

async def setup_all():
    """Complete database setup"""
    print("🚀 Setting up Guitar Registry database...")
    print("=" * 50)
    
    # Check connection
    if not await check_connection():
        return False
    
    # Create schema
    if not await create_schema():
        return False
    
    # Verify tables
    if not await check_tables():
        return False
    
    # Test integration
    if not await test_integration():
        return False
    
    print("\n" + "=" * 50)
    print("✅ Database setup completed successfully!")
    print("\nYou can now run: python test_db_integration.py")
    return True

def create_env_file():
    """Create .env file from example"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if not env_example.exists():
        print("❌ .env.example file not found")
        return False
    
    try:
        import shutil
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from .env.example")
        print("   Please update it with your database credentials")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser(description="Guitar Registry Database Setup")
    parser.add_argument("--check-connection", action="store_true", help="Check database connection")
    parser.add_argument("--create-schema", action="store_true", help="Create database schema")
    parser.add_argument("--check-tables", action="store_true", help="Check if tables exist")
    parser.add_argument("--test-integration", action="store_true", help="Test database integration")
    parser.add_argument("--setup-all", action="store_true", help="Complete setup (recommended)")
    parser.add_argument("--create-env", action="store_true", help="Create .env file from example")
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    success = True
    
    if args.create_env:
        success &= create_env_file()
    
    if args.check_connection:
        success &= await check_connection()
    
    if args.create_schema:
        success &= await create_schema()
    
    if args.check_tables:
        success &= await check_tables()
    
    if args.test_integration:
        success &= await test_integration()
    
    if args.setup_all:
        success &= await setup_all()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())