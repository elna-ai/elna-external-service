from pydantic import BaseModel


class User(BaseModel):
    principal: str
