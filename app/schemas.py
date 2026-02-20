# app/schemas.py

from pydantic import BaseModel, model_validator
from typing import List, Optional
from app.config import settings

# --- API Response Models ---

class EmployeeInfo(BaseModel):
    id: str
    name: str
    member_code: Optional[str] = None
    image_path: Optional[str] = None
    
    class Config:
        from_attributes = True

class EmployeeListResponse(BaseModel):
    employees: List[EmployeeInfo]

class StandardResponse(BaseModel):
    STATUS: int
    CODE: int
    FLAG: bool
    MESSAGE: str
    DATA: Optional[dict] = None

class FaceResult(BaseModel):
    name: str
    member_code: Optional[str] = None
    box: List[int]
    score: float

class RecognitionResponse(BaseModel):
    faces: List[FaceResult]
    
    

# ------------------ USER ---------------------

class UserInfo(BaseModel):
    id: int
    name: str
    username: str
    password: str
    mobile: str

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    name: str
    username: str
    password: str
    mobile: str

   
    
# ------------------- CLUB --------------------
    
class ClubInfo(BaseModel):
    id: int
    club_code: str
    club_name: str
    url: Optional[str] = None

    class Config:
        from_attributes = True
        
    @model_validator(mode="after")
    def add_base_url(self):
        if self.url:
            # create a new instance with updated url
            return self.model_copy(update={"url": f"{settings.SCANNER_BASE_URL}{self.url}"})
        return self
    
class ClubListResponse(BaseModel):
    clubs: List[ClubInfo]

class ClubCreateRequest(BaseModel):
    club_code: str
    club_name: str

class ClubUpdateRequest(BaseModel):
    club_code: str
    club_name: str
