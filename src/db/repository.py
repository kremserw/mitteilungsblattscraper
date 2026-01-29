"""
Repository pattern for database access.

Provides a clean interface for data operations with proper
connection management and transaction handling.
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, Edition, BulletinItem, Attachment


class Repository:
    """
    Main data access interface for the application.
    
    Implements the repository pattern with SQLite optimizations
    and automatic schema migrations.
    """
    
    def __init__(self, db_path: str = "data/mtb.db"):
        """
        Initialize repository with database path.
        
        Args:
            db_path: Path to SQLite database file
        """
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        # Create engine with optimized settings
        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True
        )
        
        # Create tables and indexes
        Base.metadata.create_all(self.engine)
        
        # Run migrations to add new columns to existing tables
        self._run_migrations()
        
        # Enable SQLite optimizations
        self._configure_sqlite()
        
        # Create session factory
        self._session_factory = sessionmaker(bind=self.engine)
        self._session: Optional[Session] = None
    
    @property
    def session(self) -> Session:
        """Get or create the current session."""
        if self._session is None:
            self._session = self._session_factory()
        return self._session
    
    def _configure_sqlite(self):
        """Apply SQLite performance optimizations."""
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB cache
            conn.execute(text("PRAGMA temp_store=MEMORY"))
            conn.commit()
    
    def _run_migrations(self):
        """Run database migrations to add missing columns."""
        with self.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(bulletin_items)"))
            existing_columns = {row[1] for row in result.fetchall()}
            
            migrations = [
                ('short_title', 'VARCHAR(200)', None),
                ('read_at', 'DATETIME', None),
                ('pdf_analysis', 'TEXT', None),
                ('pdf_analyzed_at', 'DATETIME', None),
            ]
            
            for col_name, col_type, default in migrations:
                if col_name not in existing_columns:
                    try:
                        default_clause = f" DEFAULT {default}" if default is not None else ""
                        sql = f"ALTER TABLE bulletin_items ADD COLUMN {col_name} {col_type}{default_clause}"
                        conn.execute(text(sql))
                        print(f"Migration: Added column {col_name} to bulletin_items")
                    except Exception as e:
                        print(f"Migration warning for {col_name}: {e}")
            
            conn.commit()
    
    def close(self):
        """Close database connection."""
        if self._session:
            self._session.close()
            self._session = None
    
    def commit(self):
        """Commit current transaction."""
        self.session.commit()
    
    def rollback(self):
        """Rollback current transaction."""
        self.session.rollback()
    
    # -------------------------------------------------------------------------
    # Edition methods
    # -------------------------------------------------------------------------
    
    def get_edition(self, year: int, stueck: int) -> Optional[Edition]:
        """Get a specific edition by year and issue number."""
        return self.session.query(Edition).filter_by(
            year=year, stueck=stueck
        ).first()
    
    def get_edition_by_id(self, edition_id: str) -> Optional[Edition]:
        """Get edition by string ID like '2025-15'."""
        try:
            year, stueck = edition_id.split('-')
            return self.get_edition(int(year), int(stueck))
        except (ValueError, AttributeError):
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
        return query.order_by(
            Edition.year.desc(),
            Edition.stueck.desc()
        ).all()
    
    def get_unanalyzed_editions(self) -> List[Edition]:
        """Get editions that have been scraped but not analyzed."""
        return self.session.query(Edition).filter(
            Edition.scraped_at.isnot(None),
            Edition.analyzed_at.is_(None)
        ).order_by(
            Edition.year.desc(),
            Edition.stueck.desc()
        ).all()
    
    def get_unscraped_editions(self) -> List[Edition]:
        """Get editions that haven't been scraped yet."""
        return self.session.query(Edition).filter(
            Edition.scraped_at.is_(None)
        ).order_by(
            Edition.year.desc(),
            Edition.stueck.desc()
        ).all()
    
    # -------------------------------------------------------------------------
    # Item methods
    # -------------------------------------------------------------------------
    
    def add_item(self, edition: Edition, punkt: int, **kwargs) -> BulletinItem:
        """Add an item to an edition."""
        item = BulletinItem(edition_id=edition.id, punkt=punkt, **kwargs)
        self.session.add(item)
        self.session.commit()
        return item
    
    def get_item_by_id(self, item_id: int) -> Optional[BulletinItem]:
        """Get a single item by its ID."""
        return self.session.query(BulletinItem).filter_by(id=item_id).first()
    
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
    
    def get_recent_relevant_items(
        self,
        threshold: float = 60.0,
        limit: int = 10
    ) -> List[BulletinItem]:
        """Get recent relevant items sorted by analysis date (newest first)."""
        return self.session.query(BulletinItem).filter(
            BulletinItem.relevance_score >= threshold,
            BulletinItem.analyzed_at.isnot(None)
        ).order_by(BulletinItem.analyzed_at.desc()).limit(limit).all()
    
    def update_item_analysis(
        self,
        item: BulletinItem,
        score: float,
        explanation: str,
        short_title: Optional[str] = None
    ):
        """Update analysis results for an item."""
        item.relevance_score = score
        item.relevance_explanation = explanation
        if short_title:
            item.short_title = short_title
        item.analyzed_at = datetime.now()
        self.session.commit()
    
    def update_item_pdf_analysis(self, item: BulletinItem, pdf_analysis: str):
        """Update PDF analysis results for an item."""
        item.pdf_analysis = pdf_analysis
        item.pdf_analyzed_at = datetime.now()
        self.session.commit()
    
    def mark_item_read(self, item_id: int) -> bool:
        """Mark an item as read. Returns True if successful."""
        item = self.session.query(BulletinItem).filter_by(id=item_id).first()
        if item and not item.read_at:
            item.read_at = datetime.now()
            self.session.commit()
            return True
        return False
    
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
    
    # -------------------------------------------------------------------------
    # Attachment methods
    # -------------------------------------------------------------------------
    
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
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
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


# Singleton instance management
_repository_instance: Optional[Repository] = None


def get_repository(db_path: str = "data/mtb.db") -> Repository:
    """
    Get or create repository instance.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        Repository instance
    """
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = Repository(db_path)
    return _repository_instance


# Backwards compatibility aliases
Storage = Repository
get_storage = get_repository
