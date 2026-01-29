"""
Content parser for JKU MTB Analyzer.

Handles PDF extraction and content processing.
"""

import os
import re
from typing import Optional, List, Dict
from pathlib import Path

import pdfplumber
from PyPDF2 import PdfReader


class PDFParser:
    """Parser for PDF documents."""
    
    def __init__(self, cache_dir: str = "data/cache"):
        """Initialize parser with cache directory."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file.
        Uses multiple methods for best results.
        """
        text = ""
        
        # Try pdfplumber first (better for complex layouts)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
        except Exception as e:
            print(f"pdfplumber failed: {e}")
        
        # Fallback to PyPDF2 if pdfplumber didn't work
        if not text.strip():
            try:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            except Exception as e:
                print(f"PyPDF2 failed: {e}")
        
        return self._clean_text(text)
    
    def extract_tables(self, pdf_path: str) -> List[List[List[str]]]:
        """Extract tables from PDF (useful for curricula)."""
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
        except Exception as e:
            print(f"Table extraction failed: {e}")
        
        return tables
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Fix common OCR issues
        text = text.replace('ﬁ', 'fi')
        text = text.replace('ﬂ', 'fl')
        text = text.replace('ﬀ', 'ff')
        
        # Remove page numbers and headers that repeat
        lines = text.split('\n')
        cleaned_lines = []
        seen_patterns = set()
        
        for line in lines:
            # Skip likely headers/footers
            if re.match(r'^(Seite|Page)\s*\d+\s*(von|of)?\s*\d*$', line.strip(), re.IGNORECASE):
                continue
            if re.match(r'^\d+\s*$', line.strip()):  # Just a page number
                continue
            
            # Skip repeated short lines (likely headers)
            if len(line.strip()) < 50:
                if line.strip() in seen_patterns:
                    continue
                seen_patterns.add(line.strip())
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def get_pdf_metadata(self, pdf_path: str) -> Dict:
        """Extract metadata from PDF."""
        try:
            reader = PdfReader(pdf_path)
            metadata = reader.metadata
            
            return {
                'title': metadata.get('/Title', ''),
                'author': metadata.get('/Author', ''),
                'subject': metadata.get('/Subject', ''),
                'creator': metadata.get('/Creator', ''),
                'pages': len(reader.pages),
            }
        except Exception as e:
            return {'error': str(e)}


class ContentProcessor:
    """Process and prepare content for analysis."""
    
    # Maximum tokens to send to the API (rough estimate: 1 token ≈ 4 chars)
    MAX_CONTENT_CHARS = 100000  # ~25k tokens
    
    def __init__(self):
        pass
    
    def prepare_for_analysis(
        self,
        content: str,
        attachments_text: Optional[List[str]] = None
    ) -> str:
        """
        Prepare content for LLM analysis.
        Combines main content with attachment text, handles truncation.
        """
        parts = []
        
        # Add main content
        if content:
            parts.append("=== BULLETIN CONTENT ===\n" + content)
        
        # Add attachment content
        if attachments_text:
            for i, att_text in enumerate(attachments_text):
                if att_text:
                    parts.append(f"\n=== ATTACHMENT {i+1} ===\n" + att_text)
        
        full_text = "\n\n".join(parts)
        
        # Truncate if necessary
        if len(full_text) > self.MAX_CONTENT_CHARS:
            # Keep beginning and end
            half = self.MAX_CONTENT_CHARS // 2 - 100
            full_text = (
                full_text[:half] + 
                "\n\n[... CONTENT TRUNCATED ...]\n\n" + 
                full_text[-half:]
            )
        
        return full_text
    
    def extract_key_info(self, text: str) -> Dict:
        """Extract key information from bulletin text."""
        info = {
            'dates': [],
            'ects': [],
            'programs': [],
            'positions': [],
            'deadlines': [],
        }
        
        # Extract dates
        date_patterns = [
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})',
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            info['dates'].extend(matches)
        
        # Extract ECTS values
        ects_matches = re.findall(r'(\d+)\s*ECTS', text, re.IGNORECASE)
        info['ects'] = list(set(ects_matches))
        
        # Extract study programs
        program_patterns = [
            r'(Bachelor|Master|Diplom|Doktorat)[a-zä]*studium\s+([A-Za-zäöüÄÖÜß\s]+)',
            r'(BS|MS|PhD)\s+([A-Za-zäöüÄÖÜß\s]+)',
        ]
        for pattern in program_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            info['programs'].extend([f"{m[0]} {m[1].strip()}" for m in matches])
        
        # Extract deadlines
        deadline_patterns = [
            r'(Frist|Deadline|bis spätestens|until)[:\s]+(\d{1,2}\.\d{1,2}\.\d{4})',
            r'(\d{1,2}\.\d{1,2}\.\d{4})[,\s]*(Frist|Deadline)',
        ]
        for pattern in deadline_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            info['deadlines'].extend(matches)
        
        return info
    
    def summarize_for_display(self, text: str, max_length: int = 500) -> str:
        """Create a short summary for display purposes."""
        if not text:
            return ""
        
        # Take first few sentences
        sentences = re.split(r'[.!?]\s+', text)
        summary = ""
        
        for sentence in sentences:
            if len(summary) + len(sentence) < max_length:
                summary += sentence + ". "
            else:
                break
        
        if len(summary) < 50 and len(text) > 50:
            summary = text[:max_length] + "..."
        
        return summary.strip()


def process_bulletin_item(
    item_content: str,
    attachments: List[Dict],
    pdf_parser: PDFParser,
    cache_dir: str
) -> Dict:
    """
    Process a bulletin item and its attachments.
    
    Returns dict with:
    - combined_text: All text content combined
    - extracted_info: Key extracted information
    - attachment_texts: List of text from each attachment
    """
    processor = ContentProcessor()
    attachment_texts = []
    
    # Process each attachment
    for att in attachments:
        if att.get('local_path') and os.path.exists(att['local_path']):
            text = pdf_parser.extract_text(att['local_path'])
            attachment_texts.append(text)
        elif att.get('type') == 'pdf':
            # Download and process
            filename = att.get('filename', 'document.pdf')
            safe_filename = re.sub(r'[^\w\-_.]', '_', filename)
            local_path = os.path.join(cache_dir, safe_filename)
            
            # Note: actual download would happen in scraper
            if os.path.exists(local_path):
                text = pdf_parser.extract_text(local_path)
                attachment_texts.append(text)
    
    # Combine content
    combined_text = processor.prepare_for_analysis(item_content, attachment_texts)
    
    # Extract key info
    extracted_info = processor.extract_key_info(combined_text)
    
    return {
        'combined_text': combined_text,
        'extracted_info': extracted_info,
        'attachment_texts': attachment_texts,
        'summary': processor.summarize_for_display(item_content),
    }
