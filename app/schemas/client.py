from pydantic import BaseModel, ConfigDict


class ClientAppBase(BaseModel):
    name: str
    is_active: bool = True


class ClientAppCreate(ClientAppBase):
    name: str  # Used when creating a new app reference


class ClientAppRead(ClientAppBase):
    id: int
    api_key: str  # The E-commerce app will use this key

    model_config = ConfigDict(from_attributes=True)


class ClientAppResponse(BaseModel):
    id: int
    name: str
    api_key: str
    is_active: bool

    class Config:
        from_attributes = True
