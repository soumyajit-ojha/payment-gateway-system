import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.client import ClientApp
from app.schemas.client import ClientAppCreate, ClientAppResponse
from app.core.config import settings

router = APIRouter()


@router.post("/clients", response_model=ClientAppResponse)
async def register_new_client_app(
    payload: ClientAppCreate,
    db: AsyncSession = Depends(get_db),
    x_admin_token: str = Header(...),  # Security check
):
    # 1. Protect this endpoint with a master key from .env
    if x_admin_token != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Not authorized to create clients")

    # 2. Generate a unique API Key
    new_api_key = f"pg_{uuid.uuid4().hex}"  # Example: pg_a1b2c3d4...

    # 3. Save to Database
    new_client = ClientApp(name=payload.name, api_key=new_api_key, is_active=True)

    db.add(new_client)
    await db.commit()
    await db.refresh(new_client)

    return new_client
