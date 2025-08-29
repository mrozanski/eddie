from dotenv import load_dotenv
from models.product_models import ProductSearchInput
from product_search_agent import ProductSearchAgent
from langchain_core.messages import HumanMessage

async def main():
    # Load user criteria
    try:
        input = ProductSearchInput(
            manufacturer="Fender",
            product_name="'60 Telecaster Custom",
            year="2013"
        )
        print(f"🎯 Manufacturer: {input.manufacturer}")
        print(f"🎯 Model: {input.product_name}")
        print(f"🎯 Year: {input.year}")
    except Exception as e:
        print(f"❌ Error loading user pre: {e}")
        return
    
    # Create agent with database integration enabled (default)
    # To disable database integration, use: ProductSearchAgent(input=input, enable_db=False)
    agent = ProductSearchAgent(input=input)
    await agent.setup()
    messages = await agent.run_superstep(message=[HumanMessage(content="Please research this guitar model")])
    for m in messages['messages']:
        m.pretty_print()
    
    # Clean up resources properly before event loop closes
    await agent.cleanup()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())