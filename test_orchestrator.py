import asyncio
from app.services.deployment_orchestrator import test_network

async def main():
    result = await test_network()
    print(result)

asyncio.run(main())
