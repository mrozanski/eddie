#!/usr/bin/env python3
"""
Test script to compare custom compression vs LangChain built-in tools
"""

import asyncio
from product_search_agent import ProductSearchAgent, ContentSummarizer, ContextManager
from product_search_agent_v2 import ProductSearchAgentV2, LangChainContextManager
from models.product_models import ProductSearchInput

async def test_compression_comparison():
    """Compare custom compression vs LangChain tools"""
    print("🧪 Comparing Custom vs LangChain Compression")
    print("=" * 60)
    
    # Test HTML content
    test_html = """
    <html>
        <head><title>Fender Mustang 1965</title></head>
        <body>
            <h1>Fender Mustang 1965 Specifications</h1>
            <div class="specs">
                <p><strong>Body:</strong> Poplar wood with nitrocellulose finish</p>
                <p><strong>Neck:</strong> Maple with rosewood fingerboard</p>
                <p><strong>Scale Length:</strong> 24 inches</p>
                <p><strong>Pickups:</strong> Two single-coil pickups</p>
                <p><strong>Bridge:</strong> Dynamic Vibrato system</p>
                <p><strong>Price:</strong> $239.50 USD (1965)</p>
                <p><strong>Weight:</strong> 7 lbs 8 oz</p>
            </div>
            <div class="description">
                <p>The Fender Mustang was introduced in 1964 as a student model but quickly gained popularity. 
                It features a unique switching system and comfortable short scale length. The 1965 model 
                includes the larger headstock typical of the CBS era.</p>
            </div>
            <div class="irrelevant">
                <p>This is some irrelevant content about other guitars and general music information 
                that should be filtered out during compression.</p>
            </div>
        </body>
    </html>
    """
    
    print("\n1. Testing Custom Content Summarizer...")
    custom_summarizer = ContentSummarizer()
    custom_result = custom_summarizer.extract_key_info(test_html)
    print(f"Custom result length: {len(custom_result)} characters")
    print(f"Custom result: {custom_result[:300]}...")
    
    print("\n2. Testing LangChain Context Manager...")
    try:
        langchain_manager = LangChainContextManager()
        langchain_result = langchain_manager.compress_web_content(test_html)
        print(f"LangChain result length: {len(langchain_result)} characters")
        print(f"LangChain result: {langchain_result[:300]}...")
        
        # Compare effectiveness
        print(f"\n📊 Comparison:")
        print(f"Custom compression ratio: {len(custom_result)/len(test_html)*100:.1f}%")
        print(f"LangChain compression ratio: {len(langchain_result)/len(test_html)*100:.1f}%")
        
    except Exception as e:
        print(f"❌ LangChain test failed: {e}")
    
    print("\n3. Testing Message Filtering...")
    
    # Create test messages
    test_messages = [
        "This is a relevant message about guitar specifications",
        "This is another relevant message about Fender Mustang",
        "This is an irrelevant message about cooking recipes",
        "This is a relevant message about guitar woods and pickups",
        "This is an irrelevant message about weather conditions"
    ]
    
    # Test custom filtering
    print("\nCustom filtering (simple truncation):")
    custom_context = ContextManager(max_tokens=100)
    custom_filtered = custom_context.truncate_messages(
        [{"content": msg} for msg in test_messages], 
        "system message"
    )
    print(f"Custom filtered count: {len(custom_filtered)}")
    
    # Test LangChain filtering
    print("\nLangChain filtering (intelligent relevance):")
    try:
        langchain_filtered = langchain_manager.filter_messages(
            [{"content": msg} for msg in test_messages], 
            "system message"
        )
        print(f"LangChain filtered count: {len(langchain_filtered)}")
        
    except Exception as e:
        print(f"❌ LangChain filtering failed: {e}")
    
    print("\n4. Testing Agent Initialization...")
    try:
        input_data = ProductSearchInput(
            manufacturer="Fender",
            product_name="Mustang",
            year="1965"
        )
        
        # Test custom agent
        custom_agent = ProductSearchAgent(input=input_data)
        print("✅ Custom agent initialized successfully")
        
        # Test LangChain agent
        langchain_agent = ProductSearchAgentV2(input=input_data)
        print("✅ LangChain agent initialized successfully")
        
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
    
    print("\n✅ Compression comparison completed!")

if __name__ == "__main__":
    asyncio.run(test_compression_comparison()) 