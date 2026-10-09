from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    papers = relationship("Paper", back_populates="uploader")
    ratings = relationship("Rating", back_populates="user")
    fields = relationship("UserField", back_populates="user")

class UserField(Base):
    __tablename__ = "user_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    field_name = Column(String)
    
    user = relationship("User", back_populates="fields")

class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    authors = Column(String)
    abstract = Column(Text)
    file_path = Column(String, nullable=True)
    doi = Column(String, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    uploader = relationship("User", back_populates="papers")
    tags = relationship("PaperTag", back_populates="paper")
    ratings = relationship("Rating", back_populates="paper")

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    papers = relationship("PaperTag", back_populates="tag")

class PaperTag(Base):
    __tablename__ = "paper_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"))
    tag_id = Column(Integer, ForeignKey("tags.id"))
    
    paper = relationship("Paper", back_populates="tags")
    tag = relationship("Tag", back_populates="papers")

class Rating(Base):
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    paper_id = Column(Integer, ForeignKey("papers.id"))
    rating = Column(Float)  # 1-5 scale
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="ratings")
    paper = relationship("Paper", back_populates="ratings")




