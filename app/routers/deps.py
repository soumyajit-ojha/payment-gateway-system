from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.client import ClientApp


async def get_current_client(
    x_api_key: str = Header(...), db: AsyncSession = Depends(get_db)
):
    # Check if the API key exists in our database
    query = select(ClientApp).where(
        ClientApp.api_key == x_api_key, ClientApp.is_active == True
    )
    result = await db.execute(query)
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing API Key"
        )
    return client
