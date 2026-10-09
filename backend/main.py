from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.responses import FileResponse
import requests
import re

from database import SessionLocal, engine, Base
from models import User, Paper, Tag, PaperTag, Rating, UserField
from schemas import (
    UserCreate, UserResponse, PaperCreate, PaperResponse, 
    TagCreate, RatingCreate, RecommendationResponse,
    UserFieldCreate, AdminMetrics
)
from recommender import HybridRecommender
from search import SearchEngine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Paper Recommendation Platform", version="1.0.0")
@app.get("/")
def home():
    return {"message": "API is running successfully"}

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize recommender and search engine
recommender = HybridRecommender()
search_engine = SearchEngine()

# Upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        # Ensure we always work with an int user id
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    # Always store "sub" as a string in the JWT, per JWT spec
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.get("/metadata")
def fetch_metadata(identifier: str = Query(..., description="DOI or full URL (DOI/arXiv/other)")):
    """
    Fetch basic metadata (title, authors, abstract, doi/url) for a given identifier.

    - If identifier is a DOI or DOI URL, uses Crossref to get metadata.
    - If identifier is an arXiv URL/ID, returns a link; user can fill details manually.
    """
    ident = identifier.strip()
    if not ident:
        raise HTTPException(status_code=400, detail="Identifier is required")

    # Handle arXiv links/IDs in a simple way: just echo back the URL/ID
    if "arxiv.org" in ident.lower():
        return {
            "title": "",
            "authors": "",
            "abstract": "",
            "doi": ident,
            "source": "arxiv",
        }

    # Try to extract DOI from URL if needed
    doi = ident
    if ident.lower().startswith("http"):
        if "doi.org/" in ident.lower():
            doi = ident.split("doi.org/")[-1]
        else:
            # Not a DOI URL; treat as a generic link
            return {
                "title": "",
                "authors": "",
                "abstract": "",
                "doi": ident,
                "source": "url",
            }

    doi = doi.strip()
    if not doi:
        raise HTTPException(status_code=400, detail="Could not extract DOI from identifier")

    # Call Crossref API
    url = f"https://api.crossref.org/works/{doi}"
    try:
        resp = requests.get(url, timeout=10)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to contact Crossref: {exc}")

    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Metadata not found for this DOI")

    data = resp.json().get("message", {})
    title_list = data.get("title") or []
    title = title_list[0] if title_list else ""

    authors = data.get("author") or []
    author_names = []
    for a in authors:
        given = a.get("given", "").strip()
        family = a.get("family", "").strip()
        if given and family:
            author_names.append(f"{given} {family}")
        elif given or family:
            author_names.append(given or family)
    authors_str = ", ".join(author_names)

    abstract = data.get("abstract") or ""
    if abstract:
        # Strip simple HTML tags from Crossref abstracts
        abstract = re.sub(r"<[^>]+>", "", abstract).strip()

    normalized_doi = data.get("DOI", doi)

    return {
        "title": title,
        "authors": authors_str,
        "abstract": abstract,
        "doi": normalized_doi,
        "source": "crossref",
    }


# Auth endpoints
@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = pwd_context.hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_admin=user.is_admin if hasattr(user, 'is_admin') else False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# User field endpoints
@app.post("/users/fields")
def add_user_field(
    field: UserFieldCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_field = UserField(user_id=current_user.id, field_name=field.field_name)
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field

@app.get("/users/fields")
def get_user_fields(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fields = db.query(UserField).filter(UserField.user_id == current_user.id).all()
    return fields

# Paper endpoints
@app.post("/papers", response_model=PaperResponse)
def create_paper(
    title: str = Form(...),
    authors: str = Form(...),
    abstract: str = Form(...),
    tags: str = Form(""),  # Comma-separated tags
    doi: str = Form(""),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create paper
    paper = Paper(
        title=title,
        authors=authors,
        abstract=abstract,
        doi=doi or None,
        uploaded_by=current_user.id,
    )
    
    db.add(paper)
    db.commit()
    db.refresh(paper)
    print("RECEIVED ABSTRACT:", abstract)

    
    if file:
        file_path = os.path.join(UPLOAD_DIR, f"{paper.id}_{file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        paper.file_path = file_path
        db.commit()
        db.refresh(paper)
    
    # Add tags
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        for tag_name in tag_list:
            tag = db.query(Tag).filter(Tag.name == tag_name.lower()).first()
            if not tag:
                tag = Tag(name=tag_name.lower())
                db.add(tag)
                db.commit()
                db.refresh(tag)
            
            paper_tag = PaperTag(paper_id=paper.id, tag_id=tag.id)
            db.add(paper_tag)
    
    db.commit()
    db.refresh(paper)
    
    # Update recommender
    recommender.update_paper_features(paper, db)
    
    # Add tags to response
    tags = db.query(Tag.name).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
    tag_names = [tag[0] for tag in tags]
    return PaperResponse.from_orm_with_tags(paper, tag_names)

@app.get("/papers", response_model=List[PaperResponse])
def list_papers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Paper)
    
    if search:
        query = search_engine.search_papers(query, search, db)
    
    if tag:
        query = query.join(PaperTag).join(Tag).filter(Tag.name == tag.lower())
    
    papers = query.offset(skip).limit(limit).all()
    
    # Add tags to each paper
    result = []
    for paper in papers:
        tags = db.query(Tag.name).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
        tag_names = [tag[0] for tag in tags]
        result.append(PaperResponse.from_orm_with_tags(paper, tag_names))
    
    return result

@app.get("/papers/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Add tags
    tags = db.query(Tag.name).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
    tag_names = [tag[0] for tag in tags]
    return PaperResponse.from_orm_with_tags(paper, tag_names)


@app.get("/papers/{paper_id}/file")
def get_paper_file(paper_id: int, db: Session = Depends(get_db)):
    """
    Download or open the PDF file for a paper, if it exists.
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper or not paper.file_path:
        raise HTTPException(status_code=404, detail="File not found for this paper")

    if not os.path.exists(paper.file_path):
        raise HTTPException(status_code=404, detail="File missing on server")

    # Let the browser handle inline vs download
    filename = os.path.basename(paper.file_path)
    return FileResponse(
        paper.file_path,
        media_type="application/pdf",
        filename=filename,
    )

@app.get("/papers/{paper_id}/similar", response_model=List[PaperResponse])
def get_similar_papers(paper_id: int, limit: int = 10, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    similar_papers = recommender.find_similar_papers(paper_id, limit, db)
    
    # Add tags to each paper
    result = []
    for paper in similar_papers:
        tags = db.query(Tag.name).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
        tag_names = [tag[0] for tag in tags]
        result.append(PaperResponse.from_orm_with_tags(paper, tag_names))
    
    return result

# Rating endpoints
@app.post("/papers/{paper_id}/ratings")
def create_rating(
    paper_id: int,
    rating: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Check if rating exists
    existing_rating = db.query(Rating).filter(
        Rating.user_id == current_user.id,
        Rating.paper_id == paper_id
    ).first()
    
    if existing_rating:
        existing_rating.rating = rating.rating
        db.commit()
        db.refresh(existing_rating)
        return existing_rating
    
    db_rating = Rating(
        user_id=current_user.id,
        paper_id=paper_id,
        rating=rating.rating
    )
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    
    # Update recommender
    recommender.update_user_ratings(current_user.id, db)
    
    return db_rating


@app.get("/papers/{paper_id}/ratings/me")
def get_my_rating(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the current user's rating for a given paper, if any.
    """
    rating = db.query(Rating).filter(
        Rating.user_id == current_user.id,
        Rating.paper_id == paper_id,
    ).first()

    if not rating:
        return {"rating": None}

    return {"rating": rating.rating}

# Recommendation endpoints
@app.get("/recommendations", response_model=List[RecommendationResponse])
def get_recommendations(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recommendations = recommender.get_recommendations(current_user.id, limit, db)
    return recommendations

# Tag endpoints
@app.get("/tags")
def list_tags(db: Session = Depends(get_db)):
    tags = db.query(Tag).all()
    return [{"id": tag.id, "name": tag.name, "count": len(tag.papers)} for tag in tags]

# Admin endpoints
@app.get("/admin/metrics", response_model=AdminMetrics)
def get_admin_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    total_users = db.query(User).count()
    total_papers = db.query(Paper).count()
    total_ratings = db.query(Rating).count()
    total_tags = db.query(Tag).count()
    
    # Average ratings
    avg_rating = db.query(db.func.avg(Rating.rating)).scalar() or 0
    
    # Papers per user
    papers_per_user = total_papers / total_users if total_users > 0 else 0
    
    # Top tags
    top_tags = db.query(
        Tag.name,
        db.func.count(PaperTag.tag_id).label('count')
    ).join(PaperTag).group_by(Tag.name).order_by(db.func.count(PaperTag.tag_id).desc()).limit(10).all()
    
    return {
        "total_users": total_users,
        "total_papers": total_papers,
        "total_ratings": total_ratings,
        "total_tags": total_tags,
        "average_rating": float(avg_rating),
        "papers_per_user": float(papers_per_user),
        "top_tags": [{"name": name, "count": count} for name, count in top_tags]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

