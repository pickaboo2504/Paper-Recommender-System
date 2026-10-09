from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import pandas as pd
from datetime import datetime

class SimpleRecommender:
    def __init__(self):
        self.tfidf = TfidfVectorizer(
            stop_words='english',
            max_features=2000,
            ngram_range=(1, 2)
        )
        self.paper_features = None
        self.paper_ids = []
        
    def build_features(self, db: Session):
        """Build or rebuild features from all papers"""
        from models import Paper, Tag, PaperTag
        
        papers = db.query(Paper).all()
        if not papers:
            return
        
        self.paper_ids = [p.id for p in papers]
        
        # Create feature text for each paper
        paper_texts = []
        for paper in papers:
            # Combine title, abstract, authors
            text = f"{paper.title} {paper.abstract} {paper.authors}"
            
            # Add tags
            tags = db.query(Tag.name).join(PaperTag).filter(PaperTag.paper_id == paper.id).all()
            tag_text = " ".join([tag[0] for tag in tags])
            text += f" {tag_text}"
            
            paper_texts.append(text)
        
        # Fit TF-IDF
        if paper_texts:
            self.paper_features = self.tfidf.fit_transform(paper_texts)
            print(f"✓ Recommender built with {len(paper_texts)} papers")
    
    def get_recommendations(self, user_id: int, limit: int = 10, db: Session = None):
        """Get recommendations based on user's ratings"""
        from models import Rating, Paper
        
        if db is None:
            return []
        
        print(f"Getting recommendations for user {user_id}...")
        
        # Rebuild features if needed
        if self.paper_features is None:
            self.build_features(db)
        
        # Get user's ratings
        user_ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
        print(f"User {user_id} has {len(user_ratings)} ratings")
        
        if not user_ratings:
            # If no ratings, return popular papers
            print("No ratings found, returning popular papers")
            return self._get_popular_papers(limit, db)
        
        # Find papers the user rated highly (4-5 stars)
        high_rated_paper_ids = [r.paper_id for r in user_ratings if r.rating >= 4]
        print(f"User rated {len(high_rated_paper_ids)} papers highly (4-5 stars)")
        
        if not high_rated_paper_ids:
            # If no high ratings, use all rated papers
            high_rated_paper_ids = [r.paper_id for r in user_ratings]
            print(f"Using all {len(high_rated_paper_ids)} rated papers")
        
        # Get indices of highly rated papers
        high_rated_indices = []
        for paper_id in high_rated_paper_ids:
            if paper_id in self.paper_ids:
                idx = self.paper_ids.index(paper_id)
                high_rated_indices.append(idx)
        
        if not high_rated_indices:
            print("No highly rated papers found in current features")
            return self._get_popular_papers(limit, db)
        
        print(f"Found {len(high_rated_indices)} highly rated papers in features")
        
        # Calculate average similarity to highly rated papers
        avg_similarity = np.zeros(len(self.paper_ids))
        
        for idx in high_rated_indices:
            # Get similarity of this paper to all others
            similarities = cosine_similarity(
                self.paper_features[idx:idx+1],
                self.paper_features
            ).flatten()
            avg_similarity += similarities
        
        avg_similarity /= len(high_rated_indices)
        
        # Get papers user hasn't rated
        rated_paper_ids = [r.paper_id for r in user_ratings]
        
        # Sort by similarity (descending)
        sorted_indices = np.argsort(avg_similarity)[::-1]
        
        recommendations = []
        for idx in sorted_indices:
            if len(recommendations) >= limit:
                break
            
            paper_id = self.paper_ids[idx]
            if paper_id not in rated_paper_ids:
                paper = db.query(Paper).filter(Paper.id == paper_id).first()
                if paper:
                    # Create recommendation DICTIONARY (not RecommendationResponse object)
                    reason = "Based on your highly rated papers"
                    if len(high_rated_paper_ids) == 1:
                        reason = f"Similar to paper you rated highly"
                    elif len(high_rated_paper_ids) > 1:
                        reason = f"Similar to {len(high_rated_paper_ids)} papers you rated highly"
                    
                    recommendations.append({
                        "paper_id": paper.id,
                        "title": paper.title,
                        "authors": paper.authors,
                        "abstract": paper.abstract or "",
                        "score": float(avg_similarity[idx]),
                        "reason": reason
                    })
        
        print(f"Generated {len(recommendations)} recommendation dictionaries")
        return recommendations
    
    def _get_popular_papers(self, limit: int, db: Session):
        """Get popular papers based on rating count"""
        from models import Paper, Rating
        import sqlalchemy as sa
        from schemas import RecommendationResponse
        
        # Get papers with most ratings
        subquery = db.query(
            Rating.paper_id,
            sa.func.count(Rating.id).label('rating_count'),
            sa.func.avg(Rating.rating).label('avg_rating')
        ).group_by(Rating.paper_id).subquery()
        
        papers = db.query(
            Paper,
            sa.coalesce(subquery.c.rating_count, 0).label('rating_count'),
            sa.coalesce(subquery.c.avg_rating, 0).label('avg_rating')
        ).outerjoin(subquery, Paper.id == subquery.c.paper_id)\
         .order_by(
            sa.desc('rating_count'),
            sa.desc('avg_rating'),
            sa.desc(Paper.created_at)
         ).limit(limit).all()
        
        recommendations = []
        for paper, rating_count, avg_rating in papers:
            # Calculate score: 70% based on rating count, 30% based on average rating
            rating_score = min(rating_count / 10, 1)  # Normalize to 0-1
            avg_score = avg_rating / 5  # Normalize to 0-1
            score = 0.7 * rating_score + 0.3 * avg_score
            
            recommendation = RecommendationResponse(
                paper_id=paper.id,
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract or "",
                score=float(score),
                reason=f"Popular paper ({rating_count} ratings)"
            )
            recommendations.append(recommendation)
        
        print(f"Generated {len(recommendations)} popular paper recommendations")
        return recommendations
    
    def find_similar_papers(self, paper_id: int, limit: int = 10, db: Session = None):
        """Find papers similar to the given paper"""
        from models import Paper
        
        if db is None:
            return []
        
        # Rebuild features if needed
        if self.paper_features is None:
            self.build_features(db)
        
        # Find paper index
        if paper_id not in self.paper_ids:
            return []
        
        paper_idx = self.paper_ids.index(paper_id)
        
        # Calculate similarities
        similarities = cosine_similarity(
            self.paper_features[paper_idx:paper_idx+1],
            self.paper_features
        ).flatten()
        
        # Get similar papers (exclude the paper itself)
        similar_indices = np.argsort(similarities)[::-1][1:limit+1]
        
        similar_papers = []
        for idx in similar_indices:
            paper = db.query(Paper).filter(Paper.id == self.paper_ids[idx]).first()
            if paper:
                similar_papers.append(paper)
        
        return similar_papers
    
        
    def update_recommender_after_rating(self, user_id: int, db: Session):
        """Force update recommender after a rating"""
        print(f"Force updating recommender for user {user_id}")
        
        # Rebuild features
        self.build_features(db)
        
        # Get immediate recommendations
        recommendations = self.get_recommendations(user_id, 10, db)
        
        print(f"Got {len(recommendations)} recommendations after update")
        for rec in recommendations[:3]:  # Show first 3
            print(f"  - {rec['title'][:50]}... (score: {rec['score']:.3f})")
        
        return recommendations
    
    def update_paper_features(self, paper, db: Session):
        """Update features when a new paper is added"""
        # Rebuild features to include the new paper
        self.build_features(db)
    
    def update_user_ratings(self, user_id: int, db: Session):
        """Update when user ratings change"""
        # For simple recommender, no need to rebuild
        pass