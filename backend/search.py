from sqlalchemy.orm import Query, Session
from sqlalchemy import or_

from models import Paper, Tag, PaperTag

class SearchEngine:
    def search_papers(self, query: Query, search_term: str, db: Session) -> Query:
        """Search papers by title, authors, abstract, or tags"""
        search_pattern = f"%{search_term}%"
        
        # Search in title, authors, abstract
        base_query = query.filter(
            or_(
                Paper.title.ilike(search_pattern),
                Paper.authors.ilike(search_pattern),
                Paper.abstract.ilike(search_pattern)
            )
        )
        
        # Also search in tags
        tag_ids = db.query(Tag.id).filter(Tag.name.ilike(search_pattern)).subquery()
        paper_ids_from_tags = db.query(PaperTag.paper_id).join(
            tag_ids, PaperTag.tag_id == tag_ids.c.id
        ).subquery()
        
        papers_from_tags = db.query(Paper).filter(Paper.id.in_(db.query(paper_ids_from_tags.c.paper_id)))
        
        # Combine results
        all_paper_ids = set()
        for paper in base_query.all():
            all_paper_ids.add(paper.id)
        for paper in papers_from_tags.all():
            all_paper_ids.add(paper.id)
        
        return query.filter(Paper.id.in_(all_paper_ids))

