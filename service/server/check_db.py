import asyncio
from core.database import AsyncSessionLocal
from models.trading import SystemConfig
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(SystemConfig))
        configs = res.scalars().all()
        print(f"Total configs: {len(configs)}")
        for c in configs:
            print(f"{c.key}: {c.value} ({c.category})")

if __name__ == "__main__":
    asyncio.run(run())
