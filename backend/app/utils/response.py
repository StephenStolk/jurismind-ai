from pydantic import BaseModel
from typing import Any, Optional

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    
def success_response(message: str, data: Any = None) -> APIResponse:
    return APIResponse(success=True, message=message, data=data)

def error_response(message: str, data: Any = None) -> APIResponse:
    return APIResponse(success=False, message=message, data=data)
