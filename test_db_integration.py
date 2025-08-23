#!/usr/bin/env python3
"""
Test script for database integration functionality.

This script demonstrates:
1. Database connection and manufacturer normalization
2. Fuzzy matching for manufacturer names  
3. ProductSearchAgent with database integration enabled/disabled
4. Error handling when database is unavailable

Usage:
    python test_db_integration.py
"""

import asyncio
import logging
from dotenv import load_dotenv
from models.product_models import ProductSearchInput
from product_search_agent import ProductSearchAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_database_tools():
    """Test database tools directly"""
    print("\n" + "="*50)
    print("🔍 Testing Database Tools Directly")
    print("="*50)
    
    try:
        from db_tools import initialize_database, manufacturer_lookup_tool, manufacturer_search_tool
        
        # Initialize database
        db = await initialize_database()
        if not db:
            print("❌ Database initialization failed - this is expected if database is not configured")
            print("   To fix this:")
            print("   1. Set up PostgreSQL database named 'guitar_registry'")
            print("   2. Run: psql -d guitar_registry -f database_schema.sql")
            print("   3. Update .env file with database credentials")
            print("   4. Set ENABLE_DB_TOOLS=true")
            return
        
        print("✅ Database connection established")
        
        # Test manufacturer lookup
        print("\n📋 Testing manufacturer lookup...")
        test_names = ["Gibson Corp", "Fender Musical Instruments", "PRS Guitars", "Unknown Brand"]
        
        for name in test_names:
            try:
                result = await manufacturer_lookup_tool.ainvoke({"manufacturer_name": name})
                print(f"  Input: '{name}' → {result}")
            except Exception as e:
                print(f"  Input: '{name}' → Error: {e}")
        
        # Test manufacturer search
        print("\n🔍 Testing manufacturer search...")
        search_queries = ["Gib", "Fend", "PRS", "Martin"]
        
        for query in search_queries:
            try:
                result = await manufacturer_search_tool.ainvoke({"query": query})
                print(f"  Query: '{query}' → {result}")
            except Exception as e:
                print(f"  Query: '{query}' → Error: {e}")
        
    except Exception as e:
        print(f"❌ Error testing database tools: {e}")
        print("   This indicates a code issue rather than database configuration")

async def test_agent_with_database():
    """Test ProductSearchAgent with database integration enabled"""
    print("\n" + "="*50)
    print("🤖 Testing Agent with Database Integration")
    print("="*50)
    
    try:
        # Create agent with database enabled
        input_data = ProductSearchInput(
            manufacturer="Gibson Corporation",  # Variant name to test normalization
            product_name="Les Paul Standard",
            year="2020"
        )
        
        agent = ProductSearchAgent(input=input_data, enable_db=True)
        await agent.setup()
        
        print(f"✅ Agent initialized with {len(agent.tools)} tools")
        
        # Check if database tools were added
        tool_names = [tool.name for tool in agent.tools if hasattr(tool, 'name')]
        db_tools = [name for name in tool_names if 'manufacturer' in name]
        
        if db_tools:
            print(f"🔌 Database tools available: {db_tools}")
        else:
            print("⚠️  No database tools found in agent")
        
        # Clean up
        agent.cleanup()
        
    except Exception as e:
        print(f"❌ Error testing agent with database: {e}")

async def test_agent_without_database():
    """Test ProductSearchAgent with database integration disabled"""
    print("\n" + "="*50)
    print("🤖 Testing Agent without Database Integration")
    print("="*50)
    
    try:
        # Create agent with database disabled
        input_data = ProductSearchInput(
            manufacturer="Fender",
            product_name="Stratocaster",
            year="1975"
        )
        
        agent = ProductSearchAgent(input=input_data, enable_db=False)
        await agent.setup()
        
        print(f"✅ Agent initialized with {len(agent.tools)} tools")
        
        # Check that database tools were NOT added
        tool_names = [tool.name for tool in agent.tools if hasattr(tool, 'name')]
        db_tools = [name for name in tool_names if 'manufacturer' in name]
        
        if not db_tools:
            print("✅ No database tools found (as expected)")
        else:
            print(f"⚠️  Unexpected database tools found: {db_tools}")
        
        # Clean up
        agent.cleanup()
        
    except Exception as e:
        print(f"❌ Error testing agent without database: {e}")

async def test_graceful_degradation():
    """Test that agent works gracefully when database is unavailable"""
    print("\n" + "="*50)
    print("🛡️  Testing Graceful Degradation")
    print("="*50)
    
    # Temporarily set environment to simulate database unavailability
    import os
    original_env = os.environ.get('ENABLE_DB_TOOLS')
    
    try:
        # Disable database tools via environment variable
        os.environ['ENABLE_DB_TOOLS'] = 'false'
        
        input_data = ProductSearchInput(
            manufacturer="Martin",
            product_name="D-28",
            year="1969"
        )
        
        agent = ProductSearchAgent(input=input_data, enable_db=True)  # Still enabled in code
        await agent.setup()
        
        print(f"✅ Agent initialized with {len(agent.tools)} tools despite DB disabled")
        
        # Clean up
        agent.cleanup()
        
    except Exception as e:
        print(f"❌ Error in graceful degradation test: {e}")
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ['ENABLE_DB_TOOLS'] = original_env
        elif 'ENABLE_DB_TOOLS' in os.environ:
            del os.environ['ENABLE_DB_TOOLS']

async def main():
    """Run all database integration tests"""
    load_dotenv()
    
    print("🎸 Guitar Registry Database Integration Tests")
    print("=" * 60)
    
    # Run tests
    await test_database_tools()
    await test_agent_with_database() 
    await test_agent_without_database()
    await test_graceful_degradation()
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("\nNote: Some tests may show errors if the database is not configured.")
    print("This is expected behavior for demonstration purposes.")
    print("\n💡 To set up the database for testing:")
    print("   1. Run: python setup_database.py --create-env")
    print("   2. Edit .env file with your PostgreSQL credentials")
    print("   3. Run: python setup_database.py --setup-all")
    print("   4. Re-run this test: python test_db_integration.py")

if __name__ == "__main__":
    asyncio.run(main())