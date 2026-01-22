from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.client import ClientApp


async def get_current_client(
    x_api_key: str = Header(...), db: AsyncSession = Depends(get_db)
):
    stmt = select(ClientApp).where(
        Clientapp.routers_key == x_api_key, ClientApp.is_active == True
    )
    result = await db.execute(stmt)
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return client
