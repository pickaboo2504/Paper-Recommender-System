from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    is_admin: Optional[bool] = False

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_admin: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}

class UserFieldCreate(BaseModel):
    field_name: str

class PaperCreate(BaseModel):
    title: str
    authors: str
    abstract: str
    tags: Optional[List[str]] = []
    doi: Optional[str] = None

class PaperResponse(BaseModel):
    id: int
    title: str
    authors: str
    abstract: str
    file_path: Optional[str] = None
    doi: Optional[str] = None
    uploaded_by: int
    created_at: datetime
    tags: Optional[List[str]] = []
    
    model_config = {"from_attributes": True}
    
    @classmethod
    def from_orm_with_tags(cls, paper, tags: List[str] = None):
        """Create PaperResponse with tags"""
        data = {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "file_path": paper.file_path,
            "doi": getattr(paper, "doi", None),
            "uploaded_by": paper.uploaded_by,
            "created_at": paper.created_at,
            "tags": tags or []
        }
        return cls(**data)

class TagCreate(BaseModel):
    name: str

class RatingCreate(BaseModel):
    rating: float  # 1-5 scale

class RecommendationResponse(BaseModel):
    paper: PaperResponse
    score: float
    reason: str

class AdminMetrics(BaseModel):
    total_users: int
    total_papers: int
    total_ratings: int
    total_tags: int
    average_rating: float
    papers_per_user: float
    top_tags: List[dict]

