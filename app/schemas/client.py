from pydantic import BaseModel, ConfigDict


class ClientAppBase(BaseModel):
    name: str
    is_active: bool = True


class ClientAppCreate(ClientAppBase):
    pass  # Used when creating a new app reference


class ClientAppRead(ClientAppBase):
    id: int
    api_key: str  # The E-commerce app will use this key

    model_config = ConfigDict(from_attributes=True)
