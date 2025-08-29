from dotenv import load_dotenv
from models.product_models import ProductSearchInput
from product_search_agent import ProductSearchAgent
from langchain_core.messages import HumanMessage
import json
import sys

async def main():
    # Check for JSON output mode
    json_output = "--json" in sys.argv
    
    # Load user criteria
    try:
        input = ProductSearchInput(
            manufacturer="Fender",
            product_name="'60 Telecaster Custom",
            year="2013"
        )
        if not json_output:
            print(f"🎯 Manufacturer: {input.manufacturer}")
            print(f"🎯 Model: {input.product_name}")
            print(f"🎯 Year: {input.year}")
    except Exception as e:
        if not json_output:
            print(f"❌ Error loading user pre: {e}")
        else:
            print(json.dumps({"error": f"Error loading user input: {e}"}))
        return
    
    # Create agent with structured output enabled if JSON mode
    # To disable database integration, use: enable_db=False
    agent = ProductSearchAgent(input=input, structured_output=json_output)
    await agent.setup()
    
    try:
        # Run the research workflow
        messages = await agent.run_superstep(message=[HumanMessage(content="Please research this guitar model")])
        
        if json_output:
            # Generate structured JSON output
            try:
                json_result = await agent.generate_structured_output()
                # Output clean JSON to stdout
                print(json.dumps(json_result.model_dump(), indent=2, ensure_ascii=False))
            except Exception as e:
                print(json.dumps({
                    "error": f"Failed to generate structured output: {e}",
                    "fallback": "Research completed but JSON generation failed"
                }))
        else:
            # Original natural language output
            for m in messages['messages']:
                m.pretty_print()
    
    except Exception as e:
        if json_output:
            print(json.dumps({"error": f"Research failed: {e}"}))
        else:
            print(f"❌ Error during research: {e}")
    finally:
        # Clean up resources properly before event loop closes
        await agent.cleanup()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())