from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ClientApp(BaseModel):
    __tablename__ = "client_apps"

    name = Column(String(100), nullable=False)  # e.g. "E-commerce-Prod"
    api_key = Column(String(255), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)

    # A client app can have many transactions
    transactions = relationship("Transaction", back_populates="client")
