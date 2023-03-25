from typing import Type, Any, Optional
from pydantic import BaseModel, SecretStr


class CommandData(BaseModel):
    kwargs: dict
    username: Optional[str]
    password: Optional[SecretStr]
    expression: Optional[str] 
    exit_status: bool = False

class ResponseData(BaseModel):
    response_message: str
    response_command: str | dict | None


