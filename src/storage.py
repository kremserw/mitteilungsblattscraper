"""
Database storage module for JKU MTB Analyzer.
Handles persistence of bulletin data, analysis results, and processing state.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json
import os

Base = declarative_base()


class Edition(Base):
    """Represents a single Mitteilungsblatt edition (Stück)."""
    __tablename__ = 'editions'
    
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    stueck = Column(Integer, nullable=False)  # Issue number
    
    title = Column(String(500))
    published_date = Column(DateTime)
    url = Column(String(1000))
    
    # Processing state
    scraped_at = Column(DateTime)
    analyzed_at = Column(DateTime)
    
    # Raw content
    raw_html = Column(Text)
    
    # Relationship to items
    items = relationship("BulletinItem", back_populates="edition", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Edition {self.year}-{self.stueck}>"
    
    @property
    def edition_id(self) -> str:
        """Returns human-readable edition identifier."""
        return f"{self.year}-{self.stueck}"


class BulletinItem(Base):
    """Individual item (Punkt) within a bulletin edition."""
    __tablename__ = 'bulletin_items'
    
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('editions.id'), nullable=False)
    
    punkt = Column(Integer)  # Item number
    title = Column(String(1000))
    content = Column(Text)
    category = Column(String(200))  # e.g., "Curricula", "Personalangelegenheiten", etc.
    
    # Attachments (stored as JSON list)
    attachments_json = Column(Text, default="[]")
    
    # Analysis results
    relevance_score = Column(Float)  # 0-100
    relevance_explanation = Column(Text)
    analyzed_at = Column(DateTime)
    
    # Whether user marked as relevant (override AI)
    user_marked_relevant = Column(Boolean)
    
    edition = relationship("Edition", back_populates="items")
    
    @property
    def attachments(self) -> List[Dict]:
        """Get attachments as list of dicts."""
        return json.loads(self.attachments_json or "[]")
    
    @attachments.setter
    def attachments(self, value: List[Dict]):
        """Set attachments from list of dicts."""
        self.attachments_json = json.dumps(value)
    
    def __repr__(self):
        return f"<BulletinItem {self.edition.edition_id if self.edition else '?'}-{self.punkt}>"


class Attachment(Base):
    """Downloaded attachment (PDF or other document)."""
    __tablename__ = 'attachments'
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('bulletin_items.id'))
    
    filename = Column(String(500))
    url = Column(String(1000))
    file_type = Column(String(50))  # 'pdf', 'doc', etc.
    
    # Local cache path
    local_path = Column(String(1000))
    
    # Extracted text content
    extracted_text = Column(Text)
    
    # Analysis results for this attachment
    relevance_score = Column(Float)
    relevance_explanation = Column(Text)
    
    downloaded_at = Column(DateTime)
    analyzed_at = Column(DateTime)


class Storage:
    """Main storage interface for the application."""
    
    def __init__(self, db_path: str = "data/mtb.db"):
        """Initialize storage with database path."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def close(self):
        """Close database connection."""
        self.session.close()
    
    # Edition methods
    
    def get_edition(self, year: int, stueck: int) -> Optional[Edition]:
        """Get a specific edition by year and issue number."""
        return self.session.query(Edition).filter_by(year=year, stueck=stueck).first()
    
    def get_edition_by_id(self, edition_id: str) -> Optional[Edition]:
        """Get edition by string ID like '2025-15'."""
        try:
            year, stueck = edition_id.split('-')
            return self.get_edition(int(year), int(stueck))
        except:
            return None
    
    def add_edition(self, year: int, stueck: int, **kwargs) -> Edition:
        """Add a new edition to the database."""
        edition = Edition(year=year, stueck=stueck, **kwargs)
        self.session.add(edition)
        self.session.commit()
        return edition
    
    def update_edition(self, edition: Edition, **kwargs):
        """Update an existing edition."""
        for key, value in kwargs.items():
            setattr(edition, key, value)
        self.session.commit()
    
    def get_all_editions(self, year: Optional[int] = None) -> List[Edition]:
        """Get all editions, optionally filtered by year."""
        query = self.session.query(Edition)
        if year:
            query = query.filter_by(year=year)
        return query.order_by(Edition.year.desc(), Edition.stueck.desc()).all()
    
    def get_unanalyzed_editions(self) -> List[Edition]:
        """Get editions that have been scraped but not analyzed."""
        return self.session.query(Edition).filter(
            Edition.scraped_at.isnot(None),
            Edition.analyzed_at.is_(None)
        ).order_by(Edition.year.desc(), Edition.stueck.desc()).all()
    
    def get_unscraped_editions(self) -> List[Edition]:
        """Get editions that haven't been scraped yet."""
        return self.session.query(Edition).filter(
            Edition.scraped_at.is_(None)
        ).order_by(Edition.year.desc(), Edition.stueck.desc()).all()
    
    # Item methods
    
    def add_item(self, edition: Edition, punkt: int, **kwargs) -> BulletinItem:
        """Add an item to an edition."""
        item = BulletinItem(edition_id=edition.id, punkt=punkt, **kwargs)
        self.session.add(item)
        self.session.commit()
        return item
    
    def get_relevant_items(self, threshold: float = 60.0) -> List[BulletinItem]:
        """Get all items with relevance score above threshold."""
        return self.session.query(BulletinItem).filter(
            BulletinItem.relevance_score >= threshold
        ).order_by(BulletinItem.relevance_score.desc()).all()
    
    def get_items_for_edition(self, edition: Edition) -> List[BulletinItem]:
        """Get all items for an edition."""
        return self.session.query(BulletinItem).filter_by(
            edition_id=edition.id
        ).order_by(BulletinItem.punkt).all()
    
    def clear_items_for_edition(self, edition: Edition):
        """Delete all items for an edition (for re-scraping)."""
        self.session.query(BulletinItem).filter_by(edition_id=edition.id).delete()
        edition.scraped_at = None
        edition.analyzed_at = None
        self.session.commit()
    
    def reset_edition(self, edition: Edition):
        """Reset an edition for re-scraping and re-analysis."""
        self.clear_items_for_edition(edition)
    
    def reset_all_data(self):
        """Clear all items and reset all editions."""
        self.session.query(BulletinItem).delete()
        self.session.query(Edition).update({
            Edition.scraped_at: None,
            Edition.analyzed_at: None,
            Edition.raw_html: None
        })
        self.session.commit()
    
    def update_item_analysis(self, item: BulletinItem, score: float, explanation: str):
        """Update analysis results for an item."""
        item.relevance_score = score
        item.relevance_explanation = explanation
        item.analyzed_at = datetime.now()
        self.session.commit()
    
    # Attachment methods
    
    def add_attachment(self, item_id: int, **kwargs) -> Attachment:
        """Add an attachment record."""
        attachment = Attachment(item_id=item_id, **kwargs)
        self.session.add(attachment)
        self.session.commit()
        return attachment
    
    def get_unanalyzed_attachments(self) -> List[Attachment]:
        """Get attachments that have text but haven't been analyzed."""
        return self.session.query(Attachment).filter(
            Attachment.extracted_text.isnot(None),
            Attachment.analyzed_at.is_(None)
        ).all()
    
    # Statistics
    
    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total_editions = self.session.query(Edition).count()
        scraped_editions = self.session.query(Edition).filter(
            Edition.scraped_at.isnot(None)
        ).count()
        analyzed_editions = self.session.query(Edition).filter(
            Edition.analyzed_at.isnot(None)
        ).count()
        
        total_items = self.session.query(BulletinItem).count()
        analyzed_items = self.session.query(BulletinItem).filter(
            BulletinItem.analyzed_at.isnot(None)
        ).count()
        relevant_items = self.session.query(BulletinItem).filter(
            BulletinItem.relevance_score >= 60
        ).count()
        
        return {
            "total_editions": total_editions,
            "scraped_editions": scraped_editions,
            "analyzed_editions": analyzed_editions,
            "total_items": total_items,
            "analyzed_items": analyzed_items,
            "relevant_items": relevant_items,
        }


# Singleton-like access
_storage_instance = None

def get_storage(db_path: str = "data/mtb.db") -> Storage:
    """Get or create storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = Storage(db_path)
    return _storage_instance
