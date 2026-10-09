from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
import pandas as pd

from models import Paper, Rating, Tag, PaperTag, User
from schemas import RecommendationResponse, PaperResponse

class HybridRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.content_similarity_matrix = None
        self.paper_features = {}
        self.user_ratings_matrix = None
        self.is_fitted = False
    
    def update_paper_features(self, paper: Paper, db: Session):
        """Update paper features when a new paper is added"""
        # Extract features from paper
        text_content = f"{paper.title} {paper.abstract} {paper.authors}"
        
        # Get tags
        tags = db.query(Tag).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
        tag_names = " ".join([tag.name for tag in tags])
        text_content += f" {tag_names}"
        
        self.paper_features[paper.id] = text_content
        self.is_fitted = False
    
    def update_user_ratings(self, user_id: int, db: Session):
        """Update user ratings matrix when a new rating is added"""
        self.is_fitted = False
    
    def _fit_content_based(self, db: Session):
        """Fit content-based model"""
        papers = db.query(Paper).all()
        if len(papers) < 2:
            return
        
        # Build feature vectors
        texts = []
        paper_ids = []
        for paper in papers:
            text_content = f"{paper.title} {paper.abstract} {paper.authors}"
            
            # Add tags
            tags = db.query(Tag).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
            tag_names = " ".join([tag.name for tag in tags])
            text_content += f" {tag_names}"
            
            texts.append(text_content)
            paper_ids.append(paper.id)
        
        if len(texts) > 0:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            self.content_similarity_matrix = cosine_similarity(tfidf_matrix)
            self.paper_ids = np.array(paper_ids)
            self.is_fitted = True
    
    def _fit_collaborative(self, db: Session):
        """Fit collaborative filtering model"""
        ratings = db.query(Rating).all()
        if len(ratings) == 0:
            return
        
        # Build user-item matrix
        df = pd.DataFrame([(r.user_id, r.paper_id, r.rating) for r in ratings],
                         columns=['user_id', 'paper_id', 'rating'])
        
        # Create pivot table
        user_item_matrix = df.pivot_table(
            index='user_id',
            columns='paper_id',
            values='rating',
            fill_value=0
        )
        
        # Use SVD for dimensionality reduction
        if user_item_matrix.shape[0] > 1 and user_item_matrix.shape[1] > 1:
            n_components = min(50, min(user_item_matrix.shape) - 1)
            if n_components > 0:
                svd = TruncatedSVD(n_components=n_components, random_state=42)
                user_factors = svd.fit_transform(user_item_matrix)
                item_factors = svd.components_.T
                
                self.user_factors = user_factors
                self.item_factors = item_factors
                self.user_ids = user_item_matrix.index.values
                self.paper_ids_cf = user_item_matrix.columns.values
                return
        
        self.user_factors = None
        self.item_factors = None
    
    def _ensure_fitted(self, db: Session):
        """Ensure models are fitted"""
        if not self.is_fitted:
            self._fit_content_based(db)
            self._fit_collaborative(db)
    
    def find_similar_papers(self, paper_id: int, limit: int, db: Session) -> List[Paper]:
        """Find papers similar to a given paper (content-based)"""
        self._ensure_fitted(db)
        
        if self.content_similarity_matrix is None:
            return []
        
        try:
            paper_idx = np.where(self.paper_ids == paper_id)[0]
            if len(paper_idx) == 0:
                return []
            
            paper_idx = paper_idx[0]
            similarities = self.content_similarity_matrix[paper_idx]
            
            # Get top similar papers (excluding itself)
            top_indices = np.argsort(similarities)[::-1][1:limit+1]
            
            similar_paper_ids = self.paper_ids[top_indices]
            similar_papers = db.query(Paper).filter(Paper.id.in_(similar_paper_ids)).all()
            
            # Sort by similarity score
            paper_scores = {pid: similarities[np.where(self.paper_ids == pid)[0][0]] 
                          for pid in similar_paper_ids}
            similar_papers.sort(key=lambda p: paper_scores.get(p.id, 0), reverse=True)
            
            return similar_papers
        except Exception as e:
            print(f"Error finding similar papers: {e}")
            return []
    
    def get_recommendations(self, user_id: int, limit: int, db: Session) -> List[RecommendationResponse]:
        """Get hybrid recommendations for a user"""
        self._ensure_fitted(db)
        
        # Get user's rated papers
        user_ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
        rated_paper_ids = {r.paper_id for r in user_ratings}
        
        # Content-based recommendations
        content_scores = {}
        if self.content_similarity_matrix is not None and len(user_ratings) > 0:
            for rating in user_ratings:
                if rating.rating >= 3:  # Only consider papers user liked
                    similar = self.find_similar_papers(rating.paper_id, 20, db)
                    for paper in similar:
                        if paper.id not in rated_paper_ids:
                            content_scores[paper.id] = content_scores.get(paper.id, 0) + rating.rating * 0.5
        
        # Collaborative filtering recommendations
        cf_scores = {}
        if self.user_factors is not None:
            try:
                user_idx = np.where(self.user_ids == user_id)[0]
                if len(user_idx) > 0:
                    user_idx = user_idx[0]
                    user_vector = self.user_factors[user_idx]
                    
                    # Predict ratings for all papers
                    predictions = np.dot(self.item_factors, user_vector)
                    
                    # Map to paper IDs
                    for i, paper_id in enumerate(self.paper_ids_cf):
                        if paper_id not in rated_paper_ids:
                            cf_scores[paper_id] = float(predictions[i])
            except Exception as e:
                print(f"Error in collaborative filtering: {e}")
        
        # Combine scores (weighted hybrid)
        all_paper_ids = set(content_scores.keys()) | set(cf_scores.keys())
        combined_scores = {}
        
        for paper_id in all_paper_ids:
            content_score = content_scores.get(paper_id, 0)
            cf_score = max(cf_scores.get(paper_id, 0), 0)  # Ensure non-negative
            
            # Normalize and combine (60% content, 40% collaborative)
            combined_score = 0.6 * content_score + 0.4 * cf_score
            combined_scores[paper_id] = combined_score
        
        # Get top recommendations
        sorted_papers = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # Fetch papers from database
        recommended_paper_ids = [pid for pid, _ in sorted_papers]
        papers = db.query(Paper).filter(Paper.id.in_(recommended_paper_ids)).all()
        
        # Create response with scores
        recommendations = []
        for paper in papers:
            score = combined_scores.get(paper.id, 0)
            reason = "Based on your preferences and similar users"
            if paper.id in content_scores and paper.id not in cf_scores:
                reason = "Similar to papers you liked"
            elif paper.id in cf_scores and paper.id not in content_scores:
                reason = "Liked by users with similar tastes"
            
            recommendations.append(RecommendationResponse(
                paper=PaperResponse.model_validate(paper),
                score=score,
                reason=reason
            ))
        
        return recommendations

