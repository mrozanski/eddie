#!/usr/bin/env python3
"""
Test script to verify context management fixes
"""

import asyncio
from product_search_agent import ProductSearchAgent, ContextManager, ContentSummarizer
from models.product_models import ProductSearchInput

async def test_context_management():
    """Test the context management features"""
    print("🧪 Testing Context Management Features")
    print("=" * 50)
    
    # Test 1: Content Summarizer
    print("\n1. Testing Content Summarizer...")
    summarizer = ContentSummarizer()
    
    # Simulate HTML content
    test_html = """
    <html>
        <body>
            <h1>Fender Mustang 1965</h1>
            <p>This guitar features mahogany body and maple neck.</p>
            <p>Price: $2,499 USD</p>
            <p>Pickup configuration: SS</p>
            <p>Scale length: 24 inches</p>
            <div>Lots of additional content that should be truncated...</div>
        </body>
    </html>
    """
    
    summarized = summarizer.extract_key_info(test_html)
    print(f"Original length: {len(test_html)} characters")
    print(f"Summarized length: {len(summarized)} characters")
    print(f"Summary preview: {summarized[:200]}...")
    
    # Test 2: Context Manager
    print("\n2. Testing Context Manager...")
    context_manager = ContextManager(max_tokens=1000)
    
    # Test token counting
    test_text = "This is a test message with some content."
    token_count = context_manager.count_tokens(test_text)
    print(f"Token count for '{test_text}': {token_count}")
    
    # Test 3: Agent Initialization
    print("\n3. Testing Agent Initialization...")
    try:
        input_data = ProductSearchInput(
            manufacturer="Fender",
            product_name="Mustang",
            year="1965"
        )
        
        agent = ProductSearchAgent(input=input_data)
        print("✅ Agent initialized successfully")
        print(f"Max tool calls per iteration: {agent.max_tool_calls_per_iteration}")
        print(f"Context manager max tokens: {agent.context_manager.max_tokens}")
        
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
    
    print("\n✅ Context management tests completed!")

if __name__ == "__main__":
    asyncio.run(test_context_management()) 