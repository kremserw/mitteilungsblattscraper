"""
SQLAlchemy models for JKU MTB Analyzer.

Defines the database schema for editions, bulletin items, and attachments.
"""

import html
import json
from typing import List, Dict

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean,
    ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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
    items = relationship(
        "BulletinItem",
        back_populates="edition",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Edition {self.year}-{self.stueck}>"
    
    @property
    def edition_id(self) -> str:
        """Returns human-readable edition identifier."""
        return f"{self.year}-{self.stueck}"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'year': self.year,
            'stueck': self.stueck,
            'edition_id': self.edition_id,
            'title': self.title,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'url': self.url,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'item_count': len(self.items) if self.items else 0,
        }


class BulletinItem(Base):
    """Individual item (Punkt) within a bulletin edition."""
    __tablename__ = 'bulletin_items'
    
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey('editions.id'), nullable=False)
    
    punkt = Column(Integer)  # Item number
    title = Column(String(1000))
    short_title = Column(String(200))  # AI-generated 5-7 word title
    content = Column(Text)
    category = Column(String(200))  # e.g., "Curricula", "Personalangelegenheiten"
    
    # Attachments (stored as JSON list)
    attachments_json = Column(Text, default="[]")
    
    # Analysis results
    relevance_score = Column(Float)  # 0-100
    relevance_explanation = Column(Text)
    analyzed_at = Column(DateTime)
    
    # Whether user marked as relevant (override AI)
    user_marked_relevant = Column(Boolean)
    
    # Read tracking
    read_at = Column(DateTime)  # When user first viewed this item
    
    # PDF analysis results (on-demand)
    pdf_analysis = Column(Text)  # AI analysis including PDF content
    pdf_analyzed_at = Column(DateTime)
    
    edition = relationship("Edition", back_populates="items")
    
    # Indexes for frequently queried columns
    __table_args__ = (
        Index('idx_relevance_score', 'relevance_score'),
        Index('idx_analyzed_at', 'analyzed_at'),
        Index('idx_read_at', 'read_at'),
    )
    
    @property
    def attachments(self) -> List[Dict]:
        """Get attachments as list of dicts."""
        attachments = json.loads(self.attachments_json or "[]")
        # Decode HTML entities in URLs (e.g., &amp; -> &)
        for att in attachments:
            if 'url' in att:
                att['url'] = html.unescape(att['url'])
        return attachments
    
    @attachments.setter
    def attachments(self, value: List[Dict]):
        """Set attachments from list of dicts."""
        self.attachments_json = json.dumps(value)
    
    def __repr__(self) -> str:
        edition_str = self.edition.edition_id if self.edition else '?'
        return f"<BulletinItem {edition_str}-{self.punkt}>"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'edition_id': self.edition_id,
            'edition_str': self.edition.edition_id if self.edition else None,
            'punkt': self.punkt,
            'title': self.title,
            'short_title': self.short_title,
            'category': self.category,
            'content': self.content,
            'attachments': self.attachments,
            'relevance_score': self.relevance_score,
            'relevance_explanation': self.relevance_explanation,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'pdf_analysis': self.pdf_analysis,
            'pdf_analyzed_at': self.pdf_analyzed_at.isoformat() if self.pdf_analyzed_at else None,
        }


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
    
    def __repr__(self) -> str:
        return f"<Attachment {self.filename}>"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'item_id': self.item_id,
            'filename': self.filename,
            'url': self.url,
            'file_type': self.file_type,
            'local_path': self.local_path,
            'relevance_score': self.relevance_score,
            'downloaded_at': self.downloaded_at.isoformat() if self.downloaded_at else None,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
        }
