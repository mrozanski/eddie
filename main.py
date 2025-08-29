from dotenv import load_dotenv
from models.product_models import ProductSearchInput
from product_search_agent import ProductSearchAgent
from langchain_core.messages import HumanMessage
import json
import sys
import os
from datetime import datetime

async def main():
    # Check for JSON output mode
    json_output = "--json" in sys.argv
    
    # Load user criteria
    try:
        input = ProductSearchInput(
            manufacturer="PRS",
            product_name="SE Silver Sky",
            year="2022"
        )
        if not json_output:
            print(f"🎯 Manufacturer: {input.manufacturer}")
            print(f"🎯 Model: {input.product_name}")
            print(f"🎯 Year: {input.year}")
        else:
            print(f"🎯 Researching: {input.manufacturer} {input.product_name} ({input.year})")
    except Exception as e:
        if not json_output:
            print(f"❌ Error loading user pre: {e}")
        else:
            print(f"❌ Error loading user input: {e}")
        return
    
    # Create agent with structured output enabled if JSON mode
    # To disable database integration, use: enable_db=False
    agent = ProductSearchAgent(input=input, structured_output=json_output)
    await agent.setup()
    
    try:
        # Run the research workflow
        print("🔍 Starting research workflow...")
        messages = await agent.run_superstep(message=[HumanMessage(content="Please research this guitar model")])
        print("✅ Research workflow completed")
        
        if json_output:
            # Generate structured JSON output
            try:
                print("📝 Generating structured JSON output...")
                json_result = await agent.generate_structured_output()
                
                # Create output directory if it doesn't exist
                os.makedirs("out", exist_ok=True)
                
                # Generate timestamp filename in YYYYMMDDThhmmss format
                timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
                filename = f"out/{timestamp}.json"
                
                # Save JSON to file
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(json_result.model_dump(), f, indent=2, ensure_ascii=False)
                
                print(f"💾 JSON output saved to: {filename}")
                print(f"📊 Generated {len(json_result.model_dump())} top-level fields")
                
            except Exception as e:
                print(f"❌ Failed to generate structured output: {e}")
                print("📋 Research completed but JSON generation failed")
        else:
            # Original natural language output
            for m in messages['messages']:
                m.pretty_print()
    
    except Exception as e:
        if json_output:
            print(f"❌ Research failed: {e}")
        else:
            print(f"❌ Error during research: {e}")
    finally:
        # Clean up resources properly before event loop closes
        await agent.cleanup()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())