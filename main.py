from dotenv import load_dotenv
from models.product_models import ProductSearchInput
from product_search_agent import ProductSearchAgent

async def main():
    # Load user criteria
    try:
        input = ProductSearchInput(
            manufacturer="Fender",
            product_name="Mustang",
            year="1965"
        )
        print(f"🎯 Manufacturer: {input.manufacturer}")
        print(f"🎯 Model: {input.product_name}")
        print(f"🎯 Year: {input.year}")
    except Exception as e:
        print(f"❌ Error loading user pre: {e}")
        return
    
    agent = ProductSearchAgent(input=input)
    await agent.setup()
    messages =await agent.run_superstep(message="")
    for m in messages['messages']:
        m.pretty_print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())