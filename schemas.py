from pydantic import BaseModel
from datetime import datetime

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class ChatBase(BaseModel):
    user_input: str
    ai_response: str

class ChatCreate(ChatBase):
    pass

class Chat(ChatBase):
    id: int
    timestamp: datetime
    user_id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None