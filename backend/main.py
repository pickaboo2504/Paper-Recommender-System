from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func  
from typing import List, Optional
import os
import shutil
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.responses import FileResponse
import requests
import re
import fitz  # PyMuPDF
from pdfminer.high_level import extract_text
import io
from PIL import Image
import pytesseract

from database import SessionLocal, engine, Base
from models import User, Paper, Tag, PaperTag, Rating, UserField
from schemas import (
    UserCreate, UserResponse, PaperCreate, PaperResponse, 
    TagCreate, RatingCreate, RecommendationResponse,
    UserFieldCreate, AdminMetrics
)
from recommender import HybridRecommender
from simple_recommender import SimpleRecommender
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
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
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
recommender = SimpleRecommender()
search_engine = SearchEngine()

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
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


# =========== RATING ENDPOINTS ===========

@app.get("/papers/{paper_id}/ratings/me")
def get_my_rating(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the current user's rating for a given paper, if any.
    Returns {"rating": 0} if not rated yet.
    """
    print(f"🔍 Getting user's rating for paper {paper_id}")
    
    rating = db.query(Rating).filter(
        Rating.user_id == current_user.id,
        Rating.paper_id == paper_id,
    ).first()

    if not rating:
        print(f"ℹ️ No rating found for paper {paper_id}")
        return {"rating": 0}  # Consistent format

    print(f"✅ Found rating: {rating.rating} stars")
    return {"rating": float(rating.rating)}


@app.get("/papers/{paper_id}/ratings/summary")
def get_rating_summary(
    paper_id: int,
    db: Session = Depends(get_db),
):
    """
    Return rating summary for a paper.
    """
    from sqlalchemy import func
    
    ratings = db.query(Rating).filter(Rating.paper_id == paper_id).all()
    
    if not ratings:
        return {
            "average": 0,
            "count": 0,
            "distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        }
    
    # Calculate average
    avg_result = db.query(func.avg(Rating.rating)).filter(Rating.paper_id == paper_id).scalar()
    average = float(avg_result) if avg_result else 0
    
    # Calculate distribution
    distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for rating in ratings:
        distribution[str(rating.rating)] += 1
    
    return {
        "average": round(average, 2),
        "count": len(ratings),
        "distribution": distribution
    }


@app.post("/papers/{paper_id}/ratings")
def create_rating(
    paper_id: int,
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update a rating for a paper.
    Returns a SINGLE object (not an array).
    """
    print(f"📝 Rating request - User: {current_user.id}, Paper: {paper_id}, Rating: {rating_data.rating}")
    
    # Check if paper exists
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        print(f" Paper {paper_id} not found")
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Validate rating is between 1-5
    if rating_data.rating < 1 or rating_data.rating > 5:
        print(f" Invalid rating: {rating_data.rating}")
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Check if rating already exists
    existing_rating = db.query(Rating).filter(
        Rating.user_id == current_user.id,
        Rating.paper_id == paper_id
    ).first()
    
    response_data = {}
    
    if existing_rating:
        # Update existing rating
        print(f"🔄 Updating rating from {existing_rating.rating} to {rating_data.rating}")
        existing_rating.rating = rating_data.rating
        db.commit()
        
        response_data = {
            "success": True,
            "message": "Rating updated successfully",
            "rating": float(rating_data.rating),
            "paper_id": paper_id,
            "user_id": current_user.id
        }
    else:
        # Create new rating
        print(f" Creating new rating")
        db_rating = Rating(
            user_id=current_user.id,
            paper_id=paper_id,
            rating=rating_data.rating
        )
        db.add(db_rating)
        db.commit()
        
        response_data = {
            "success": True,
            "message": "Rating saved successfully",
            "rating": float(rating_data.rating),
            "paper_id": paper_id,
            "user_id": current_user.id
        }
    

    print(f" Returning response: {response_data}")
    return response_data


# Upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
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

def extract_pdf_metadata(file_path: str):
    """
    Extract metadata from PDF file including OCR for scanned documents.
    """
    metadata = {
        "title": "",
        "authors": "",
        "abstract": "",
        "doi": "",
        "content": ""
    }
    
    try:
        # Open PDF
        pdf_document = fitz.open(file_path)
        
        # Extract metadata from PDF info
        pdf_metadata = pdf_document.metadata
        if pdf_metadata:
            metadata["title"] = pdf_metadata.get("title", "").strip()
            metadata["authors"] = pdf_metadata.get("author", "").strip()
        
        # Try to extract text from first few pages
        text_content = ""
        max_pages = min(5, len(pdf_document))  # First 5 pages or less
        
        for page_num in range(max_pages):
            page = pdf_document[page_num]
            
            # Try to extract text directly
            page_text = page.get_text()
            
            # If no text found or very little text, try OCR
            if not page_text.strip() or len(page_text.strip()) < 100:
                # Render page as image
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Perform OCR
                page_text = pytesseract.image_to_string(image)
            
            text_content += page_text + "\n"
        
        metadata["content"] = text_content
        
        # Try to find DOI in text
        doi_pattern = r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b'
        matches = re.findall(doi_pattern, text_content, re.IGNORECASE)
        if matches:
            metadata["doi"] = matches[0]
        
        # Try to find abstract (common patterns)
        abstract_section = ""
        
        # Look for "Abstract" section
        abstract_patterns = [
            r'(?:Abstract|ABSTRACT)\s*[\n:]?\s*(.+?)(?=\n\s*\n|\n\s*[A-Z0-9]|Introduction|INTRODUCTION|$)',
            r'Summary\s*[\n:]?\s*(.+?)(?=\n\s*\n|\n\s*[A-Z0-9]|Introduction|INTRODUCTION|$)',
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, text_content, re.DOTALL | re.IGNORECASE)
            if match:
                abstract_text = match.group(1).strip()
                if len(abstract_text) > 20:  # Ensure it's a real abstract
                    abstract_section = abstract_text
                    break
        
        if not abstract_section:
            # Try to find the first paragraph if no abstract found
            paragraphs = re.split(r'\n\s*\n', text_content)
            if len(paragraphs) > 1:
                first_para = paragraphs[0].strip()
                if len(first_para) > 50 and len(first_para) < 2000:
                    abstract_section = first_para
        
        if abstract_section:
            # Clean up the abstract
            abstract_section = re.sub(r'\s+', ' ', abstract_section)  # Normalize whitespace
            abstract_section = abstract_section[:1500]  # Limit length
            metadata["abstract"] = abstract_section
        
        # If title is still empty, try to extract from first line
        if not metadata["title"] and text_content:
            lines = text_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and len(line) < 200:
                    metadata["title"] = line
                    break
        
        pdf_document.close()
        
    except Exception as e:
        print(f"Error extracting PDF metadata: {e}")
    
    return metadata

@app.get("/metadata")

def fetch_metadata(identifier: str = Query(..., description="DOI or full URL (DOI/arXiv/other)")):
    """
    Fetch basic metadata (title, authors, abstract, doi/url) for a given identifier.
    """
    ident = identifier.strip()
    if not ident:
        raise HTTPException(status_code=400, detail="Identifier is required")

    # Handle arXiv links/IDs
    if "arxiv.org" in ident.lower():
        # Extract arXiv ID
        arxiv_pattern = r'arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9v]+)'
        match = re.search(arxiv_pattern, ident, re.IGNORECASE)
        arxiv_id = match.group(1) if match else ident
        
        # For arXiv, we might want to use the arXiv API
        try:
            arxiv_id_clean = arxiv_id.split('v')[0]  # Remove version
            arxiv_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id_clean}"
            arxiv_resp = requests.get(arxiv_url, timeout=10)
            
            if arxiv_resp.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(arxiv_resp.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                
                title = ""
                authors = []
                abstract = ""
                
                # Extract title
                title_elem = root.find('.//atom:title', ns)
                if title_elem is not None:
                    title = title_elem.text.strip()
                
                # Extract authors
                for author_elem in root.findall('.//atom:author/atom:name', ns):
                    if author_elem is not None and author_elem.text:
                        authors.append(author_elem.text.strip())
                
                # Extract summary (abstract)
                summary_elem = root.find('.//atom:summary', ns)
                if summary_elem is not None and summary_elem.text:
                    abstract = summary_elem.text.strip()
                    # Clean up abstract
                    abstract = re.sub(r'\s+', ' ', abstract)
                
                return {
                    "title": title,
                    "authors": ", ".join(authors),
                    "abstract": abstract,
                    "doi": f"https://arxiv.org/abs/{arxiv_id_clean}",
                    "source": "arxiv",
                }
        except Exception as e:
            print(f"Failed to fetch arXiv metadata: {e}")
        
        return {
            "title": "",
            "authors": "",
            "abstract": "",
            "doi": f"https://arxiv.org/abs/{arxiv_id}" if match else ident,
            "source": "arxiv",
        }

    # Try to extract DOI from URL if needed
    doi = ident
    if ident.lower().startswith("http"):
        if "doi.org/" in ident.lower():
            # Extract DOI from doi.org URL
            doi_match = re.search(r'doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', ident, re.IGNORECASE)
            if doi_match:
                doi = doi_match.group(1)
            else:
                doi = ident.split("doi.org/")[-1].strip('/')
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

    # Remove any URL encoding
    doi = requests.utils.unquote(doi)
    
    # Ensure DOI starts with 10.
    if not doi.startswith("10."):
        doi = f"10.{doi}"
    
    # Call Crossref API
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "PaperRecommendationPlatform/1.0 (mailto:admin@example.com)"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to contact Crossref: {exc}")

    if resp.status_code != 200:
        # Try without the 10. prefix
        if doi.startswith("10.10."):
            doi = doi[3:]  # Remove extra "10."
            url = f"https://api.crossref.org/works/{doi}"
            resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            raise HTTPException(
                status_code=404, 
                detail=f"Metadata not found for DOI: {doi}. Status: {resp.status_code}"
            )

    data = resp.json().get("message", {})
    
    # Extract title
    title_list = data.get("title") or []
    title = title_list[0] if title_list else ""
    
    # Extract authors
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

    # Extract abstract - Crossref often puts abstracts in a special format
    abstract = ""
    
    # Method 1: Check for abstract in multiple possible locations
    if data.get("abstract"):
        # Crossref abstracts are often in JATS XML format
        import html
        abstract_html = data.get("abstract")
        
        # Try to parse JATS XML abstract
        jats_match = re.search(r'<jats:p>(.+?)</jats:p>', abstract_html, re.DOTALL | re.IGNORECASE)
        if jats_match:
            abstract = jats_match.group(1)
            # Clean HTML tags
            abstract = re.sub(r'<[^>]+>', '', abstract)
        else:
            # Try to clean any HTML tags
            abstract = re.sub(r'<[^>]+>', '', abstract_html)
    
    # Method 2: Try alternative abstract fields
    if not abstract:
        abstract_fields = [
            data.get("description"),
            data.get("summary"),
            data.get("abstract-text"),
        ]
        
        for field in abstract_fields:
            if field:
                if isinstance(field, list) and field:
                    abstract = field[0]
                    break
                elif isinstance(field, str):
                    abstract = field
                    break
    
    # Method 3: Some papers have abstract in a different format
    if not abstract and isinstance(data.get("abstract"), str):
        abstract = data.get("abstract")
        # Clean JATS tags if present
        abstract = re.sub(r'<jats:[^>]+>', '', abstract)
        abstract = re.sub(r'</jats:[^>]+>', '', abstract)
    
    # Clean up abstract
    if abstract:
        # Remove any remaining HTML/XML tags
        abstract = re.sub(r'<[^>]+>', '', abstract)
        # Decode HTML entities
        abstract = html.unescape(abstract) if 'html' in locals() else abstract
        # Normalize whitespace
        abstract = re.sub(r'\s+', ' ', abstract).strip()
        # Limit length
        if len(abstract) > 3000:
            abstract = abstract[:3000] + "..."
    
    normalized_doi = data.get("DOI", doi)

    return {
        "title": title,
        "authors": authors_str,
        "abstract": abstract,
        "doi": normalized_doi,
        "source": "crossref",
    }


@app.post("/recommendations/rebuild")
def rebuild_recommender(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually rebuild the recommender system (useful for testing)"""
    try:
        recommender.build_features(db)
        return {"message": "Recommender rebuilt successfully", "papers_count": len(recommender.paper_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild recommender: {str(e)}")
    

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

@app.post("/extract-pdf-metadata")
async def extract_pdf_metadata_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Extract metadata from a PDF file without saving it to database.
    """
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save file temporarily
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"temp_{file.filename}")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract metadata
        metadata = extract_pdf_metadata(temp_file_path)
        
        # Clean up temp file
        os.remove(temp_file_path)
        
        # If DOI was found, try to fetch additional metadata from Crossref
        if metadata.get("doi"):
            try:
                crossref_data = fetch_metadata(metadata["doi"])
                # Merge with extracted metadata (prefer extracted if exists)
                if not metadata.get("title") and crossref_data.get("title"):
                    metadata["title"] = crossref_data["title"]
                if not metadata.get("authors") and crossref_data.get("authors"):
                    metadata["authors"] = crossref_data["authors"]
                if not metadata.get("abstract") and crossref_data.get("abstract"):
                    metadata["abstract"] = crossref_data["abstract"]
            except Exception as e:
                print(f"Failed to fetch Crossref data: {e}")
                # Continue with extracted metadata only
        
        return metadata
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract metadata: {str(e)}")
    finally:
        # Clean up if file exists
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass

# Paper endpoints
@app.post("/papers", response_model=PaperResponse)
def create_paper(
    title: str = Form(...),
    authors: str = Form(...),
    abstract: str = Form(...),
    tags: str = Form(""),  # Comma-separated tags
    doi: str = Form(""),
    file: Optional[UploadFile] = File(None),
    extract_metadata: bool = Form(True),  # New parameter
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # If file is provided and extract_metadata is True, try to enhance metadata
    extracted_metadata = {}
    
    if file and extract_metadata and file.filename.lower().endswith('.pdf'):
        try:
            # Save file temporarily
            temp_file_path = os.path.join(UPLOAD_DIR, f"temp_{file.filename}")
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Extract metadata from PDF
            extracted_metadata = extract_pdf_metadata(temp_file_path)
            
            # Use extracted metadata to enhance user input
            if extracted_metadata.get("title") and (not title or title.strip() == ""):
                title = extracted_metadata["title"]
            if extracted_metadata.get("authors") and (not authors or authors.strip() == ""):
                authors = extracted_metadata["authors"]
            if extracted_metadata.get("abstract") and (not abstract or abstract.strip() == ""):
                abstract = extracted_metadata["abstract"]
            if extracted_metadata.get("doi") and (not doi or doi.strip() == ""):
                doi = extracted_metadata["doi"]
            
            # Reset file pointer for later use
            file.file.seek(0)
            
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
        except Exception as e:
            print(f"Failed to extract metadata from PDF: {e}")
    
    # Validate required fields
    if not title or title.strip() == "":
        raise HTTPException(status_code=400, detail="Title is required")
    
    # Create paper
    paper = Paper(
        title=title.strip(),
        authors=authors.strip() if authors else "",
        abstract=abstract.strip() if abstract else "",
        doi=doi.strip() if doi else None,
        uploaded_by=current_user.id,
    )
    
    db.add(paper)
    db.commit()
    db.refresh(paper)
    
    # Save file permanently
    if file:
       
        file_extension = os.path.splitext(file.filename)[1]
        file_path = os.path.join(UPLOAD_DIR, f"{paper.id}{file_extension}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        paper.file_path = file_path
        db.commit()
        db.refresh(paper)
    
    # Add tags
    if tags and tags.strip():
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        for tag_name in tag_list:
            tag = db.query(Tag).filter(Tag.name == tag_name.lower()).first()
            if not tag:
                tag = Tag(name=tag_name.lower())
                db.add(tag)
                db.commit()
                db.refresh(tag)
            
            # Check if tag is already associated
            existing = db.query(PaperTag).filter(
                PaperTag.paper_id == paper.id,
                PaperTag.tag_id == tag.id
            ).first()
            
            if not existing:
                paper_tag = PaperTag(paper_id=paper.id, tag_id=tag.id)
                db.add(paper_tag)
    
    db.commit()
    db.refresh(paper)
    
    # Update recommender
    try:
        recommender.update_paper_features(paper, db)
    except Exception as e:
        print(f"Error updating recommender: {e}")
    
    # Add tags to response
    tags_result = db.query(Tag.name).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
    tag_names = [tag[0] for tag in tags_result]
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
    
    papers = query.order_by(Paper.created_at.desc()).offset(skip).limit(limit).all()
    
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
    
    # Increment view count
    paper.views = (paper.views or 0) + 1
    db.commit()
    db.refresh(paper)
    
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



@app.get("/recommendations")
def get_recommendations(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print(f"\n=== SIMPLE RECOMMENDER for user {current_user.id} ===")

    try:
        # Ensure paper features are created
        if recommender.paper_features is None:
            print("Building features for the first time...")
            recommender.build_features(db)

        # Get SIMPLE recommendations (NOT the hybrid)
        recs = recommender.get_recommendations(
            user_id=current_user.id,
            limit=limit,
            db=db
        )

        print(f"Simple recommender returned {len(recs)} items")

        # Always return something
        if len(recs) == 0:
            print("Simple recommender empty → using emergency fallback")
            return get_emergency_recommendations(limit, db)

        return recs

    except Exception as e:
        print(f"Error in simple recommender: {e}")
        import traceback
        print(traceback.format_exc())
        return get_emergency_recommendations(limit, db)



def get_emergency_recommendations(limit: int, db: Session):
    """Emergency fallback that always returns something"""
    print(" EMERGENCY: Creating recommendations from all papers")
    
    # Get all papers
    all_papers = db.query(Paper).order_by(Paper.created_at.desc()).limit(limit * 2).all()
    
    recommendations = []
    for i, paper in enumerate(all_papers[:limit]):
        # Get tags
        tags = db.query(Tag.name).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
        tag_names = [t[0] for t in tags]
        
        # Simple scoring based on order
        score = 0.5 + (i * 0.05)
        
        reasons = [
            "Recommended for you",
            "Featured paper in our collection",
            "Based on trending topics",
            "Popular in academic circles",
            "Highly relevant research"
        ]
        
        import random
        reason = random.choice(reasons)
        if tag_names:
            reason += f" (topics: {', '.join(tag_names[:2])})"
        
        recommendations.append({
            "paper_id": paper.id,
            "title": paper.title,
            "authors": paper.authors or "",
            "abstract": paper.abstract[:200] + "..." if paper.abstract and len(paper.abstract) > 200 else (paper.abstract or ""),
            "score": round(score, 3),
            "reason": reason
        })
    
    print(f"Emergency returning {len(recommendations)} recommendations")
    return recommendations
@app.get("/debug/check-recommender")
def check_recommender_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check why recommender returns 0 recommendations"""
    
    status = {
        "user_id": current_user.id,
        "recommender_built": recommender.paper_features is not None,
        "paper_count": len(recommender.paper_ids) if recommender.paper_ids else 0,
    }
    
    # Check user's ratings
    user_ratings = db.query(Rating).filter(Rating.user_id == current_user.id).all()
    status["user_ratings_count"] = len(user_ratings)
    status["user_ratings"] = [
        {"paper_id": r.paper_id, "rating": r.rating} for r in user_ratings
    ]
    
    # Total ratings in system
    total_ratings = db.query(Rating).count()
    total_papers = db.query(Paper).count()
    total_users = db.query(User).count()
    
    status.update({
        "total_ratings": total_ratings,
        "total_papers": total_papers,
        "total_users": total_users,
        "ratings_per_user": total_ratings / total_users if total_users > 0 else 0,
        "ratings_per_paper": total_ratings / total_papers if total_papers > 0 else 0
    })
    
    # Try to get recommendations manually
    try:
        if not status["recommender_built"]:
            recommender.build_features(db)
            
        # Get raw recommendations
        raw_recs = recommender.get_recommendations(current_user.id, 5, db)
        status["raw_recommendations"] = raw_recs
        status["recommendations_count"] = len(raw_recs)
        
        # Debug: what does the recommender return?
        status["debug_info"] = {
            "paper_ids": recommender.paper_ids[:10] if recommender.paper_ids else [],
            "paper_features_shape": recommender.paper_features.shape if recommender.paper_features is not None else None,
            "user_factors_shape": recommender.user_factors.shape if recommender.user_factors is not None else None,
            "item_factors_shape": recommender.item_factors.shape if recommender.item_factors is not None else None
        }
        
    except Exception as e:
        status["error"] = str(e)
    
    return status




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
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_papers = db.query(Paper).filter(Paper.created_at >= seven_days_ago).count()
    recent_ratings = db.query(Rating).filter(Rating.created_at >= seven_days_ago).count()
    
    return {
        "total_users": total_users,
        "total_papers": total_papers,
        "total_ratings": total_ratings,
        "total_tags": total_tags,
        "average_rating": float(avg_rating),
        "papers_per_user": float(papers_per_user),
        "recent_papers": recent_papers,
        "recent_ratings": recent_ratings,
        "top_tags": [{"name": name, "count": count} for name, count in top_tags]
    }




@app.post("/debug/rebuild-recommender")
def debug_rebuild_recommender(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force rebuild the recommender system"""
    try:
        recommender.build_features(db)
        return {
            "message": "Recommender rebuilt successfully",
            "papers_count": len(recommender.paper_ids),
            "features_built": recommender.paper_features is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild recommender: {str(e)}")


@app.get("/test/recommendations")
def test_recommendations(
    db: Session = Depends(get_db)
):
    """Test endpoint that doesn't require authentication"""
    print("🧪 TEST: Getting recommendations without auth")
    
    # Create a mock user context
    from unittest.mock import Mock
    
    # Get any user from database
    user = db.query(User).first()
    if not user:
        return {"error": "No users in database"}
    
    # Get recommendations for this user
    recommendations = get_recommendations(limit=5, current_user=user, db=db)
    
    return {
        "test_user": {
            "id": user.id,
            "email": user.email
        },
        "recommendations_count": len(recommendations),
        "recommendations": recommendations
    }

#admin endpoint
@app.get("/admin/metrics/overview")
def get_admin_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alias for /admin/metrics to match frontend"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    total_users = db.query(User).count()
    total_papers = db.query(Paper).count()
    total_ratings = db.query(Rating).count()
    total_tags = db.query(Tag).count()
    
    # Average ratings
    from sqlalchemy import func  # Make sure this import is at top of file
    avg_rating = db.query(func.avg(Rating.rating)).scalar() or 0
    
    # Papers per user
    papers_per_user = total_papers / total_users if total_users > 0 else 0
    
    # Top tags
    top_tags = db.query(
        Tag.name,
        func.count(PaperTag.tag_id).label('count')
    ).join(PaperTag).group_by(Tag.name).order_by(func.count(PaperTag.tag_id).desc()).limit(10).all()
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_papers = db.query(Paper).filter(Paper.created_at >= seven_days_ago).count()
    recent_ratings = db.query(Rating).filter(Rating.created_at >= seven_days_ago).count()
    
    return {
        "total_users": total_users,
        "total_papers": total_papers,
        "total_ratings": total_ratings,
        "total_tags": total_tags,
        "average_rating": float(avg_rating),
        "papers_per_user": float(papers_per_user),
        "recent_papers": recent_papers,
        "recent_ratings": recent_ratings,
        "top_tags": [{"name": name, "count": count} for name, count in top_tags]
    }


@app.get("/admin/metrics/users")
def get_admin_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users for admin dashboard"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        papers_count = db.query(Paper).filter(Paper.uploaded_by == user.id).count()
        ratings_count = db.query(Rating).filter(Rating.user_id == user.id).count()
        
        result.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "papers_count": papers_count,
            "ratings_count": ratings_count,
            "fields": []
        })
    
    return result


@app.get("/admin/metrics/papers")
def get_admin_papers(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get papers for admin dashboard"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    papers = db.query(Paper).order_by(Paper.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for paper in papers:
        uploader = db.query(User).filter(User.id == paper.uploaded_by).first()
        ratings_count = db.query(Rating).filter(Rating.paper_id == paper.id).count()
        
        # Calculate average rating
        from sqlalchemy import func
        avg_rating = db.query(func.avg(Rating.rating)).filter(Rating.paper_id == paper.id).scalar() or 0
        
        # Get tags
        tags = db.query(Tag.name).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
        tag_names = [tag[0] for tag in tags]
        
        result.append({
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "uploaded_by": uploader.email if uploader else "Unknown",
            "uploaded_by_id": paper.uploaded_by,
            "created_at": paper.created_at.isoformat() if paper.created_at else None,
            "ratings_count": ratings_count,
            "average_rating": float(avg_rating),
            "has_file": bool(paper.file_path),
            "tags": tag_names
        })
    
    return result


@app.get("/admin/metrics/activity")
def get_admin_activity(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get activity data (simplified)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Return empty activity for now
    activity_data = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
        activity_data.append({
            "date": date,
            "papers": 0,
            "ratings": 0,
            "users": 0
        })
    
    activity_data.reverse()
    
    return {
        "period_days": days,
        "activity": activity_data
    }


@app.get("/admin/metrics/recommender")
def get_admin_recommender_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recommender stats"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "papers_in_system": len(recommender.paper_ids) if recommender.paper_ids else 0,
        "features_built": recommender.paper_features is not None,
        "feature_dimensions": 0,
        "last_feature_update": datetime.utcnow().isoformat()
    }


@app.post("/admin/metrics/rebuild-recommender")
def admin_rebuild_recommender(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rebuild recommender"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        recommender.build_features(db)
        return {
            "success": True,
            "message": "Recommender rebuilt successfully",
            "papers_processed": len(recommender.paper_ids)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to rebuild recommender: {str(e)}"
        }



@app.get("/admin/metrics/overview", response_model=AdminMetrics)
def get_admin_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alias for frontend - same as /admin/metrics"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    total_users = db.query(User).count()
    total_papers = db.query(Paper).count()
    total_ratings = db.query(Rating).count()
    total_tags = db.query(Tag).count()
    
    # Fix: Use func.avg, not db.func.avg
    avg_rating = db.query(func.avg(Rating.rating)).scalar() or 0
    
    # Papers per user
    papers_per_user = total_papers / total_users if total_users > 0 else 0
    
    # Top tags - use func.count
    top_tags = db.query(
        Tag.name,
        func.count(PaperTag.tag_id).label('count')
    ).join(PaperTag).group_by(Tag.name).order_by(func.count(PaperTag.tag_id).desc()).limit(10).all()
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_papers = db.query(Paper).filter(Paper.created_at >= seven_days_ago).count()
    recent_ratings = db.query(Rating).filter(Rating.created_at >= seven_days_ago).count()
    
    return {
        "total_users": total_users,
        "total_papers": total_papers,
        "total_ratings": total_ratings,
        "total_tags": total_tags,
        "average_rating": float(avg_rating),
        "papers_per_user": float(papers_per_user),
        "recent_papers": recent_papers,
        "recent_ratings": recent_ratings,
        "top_tags": [{"name": name, "count": count} for name, count in top_tags]
    }


@app.get("/admin/metrics/users")
def get_admin_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users for admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        papers_count = db.query(Paper).filter(Paper.uploaded_by == user.id).count()
        ratings_count = db.query(Rating).filter(Rating.user_id == user.id).count()
        
        result.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "papers_count": papers_count,
            "ratings_count": ratings_count,
            "fields": []
        })
    
    return result


@app.get("/admin/metrics/papers")
def get_admin_papers(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get papers for admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    papers = db.query(Paper).order_by(Paper.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for paper in papers:
        uploader = db.query(User).filter(User.id == paper.uploaded_by).first()
        ratings_count = db.query(Rating).filter(Rating.paper_id == paper.id).count()
        
        # Calculate average rating
        avg_rating = db.query(func.avg(Rating.rating)).filter(Rating.paper_id == paper.id).scalar() or 0
        
        # Get tags
        tags = db.query(Tag.name).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
        tag_names = [tag[0] for tag in tags]
        
        result.append({
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "uploaded_by": uploader.email if uploader else "Unknown",
            "uploaded_by_id": paper.uploaded_by,
            "created_at": paper.created_at.isoformat() if paper.created_at else None,
            "ratings_count": ratings_count,
            "average_rating": float(avg_rating),
            "has_file": bool(paper.file_path),
            "tags": tag_names
        })
    
    return result


@app.get("/admin/metrics/activity")
def get_admin_activity(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get activity data"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Return empty activity for now
    activity_data = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
        activity_data.append({
            "date": date,
            "papers": 0,
            "ratings": 0,
            "users": 0
        })
    
    activity_data.reverse()
    
    return {
        "period_days": days,
        "activity": activity_data
    }


@app.get("/admin/metrics/recommender")
def get_admin_recommender_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recommender stats"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "papers_in_system": len(recommender.paper_ids) if recommender.paper_ids else 0,
        "features_built": recommender.paper_features is not None,
        "feature_dimensions": 0,
        "last_feature_update": datetime.utcnow().isoformat()
    }


@app.post("/admin/metrics/rebuild-recommender")
def admin_rebuild_recommender(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rebuild recommender"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        recommender.build_features(db)
        return {
            "success": True,
            "message": "Recommender rebuilt successfully",
            "papers_processed": len(recommender.paper_ids)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to rebuild recommender: {str(e)}"
        }   
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)