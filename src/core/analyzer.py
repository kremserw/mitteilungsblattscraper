"""
AI Analyzer for JKU MTB content.

Uses Claude Haiku for relevance scoring and content analysis.
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import anthropic
import requests

from ..db.models import Edition, BulletinItem
from ..db.repository import Repository
from .parser import PDFParser, ContentProcessor, process_bulletin_item


class RelevanceAnalyzer:
    """Analyzes bulletin content for relevance using Claude Haiku."""
    
    DEFAULT_MODEL = "claude-haiku-4-5"
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Initialize with Anthropic API key.
        
        Args:
            api_key: Anthropic API key
            model: Model to use (defaults to claude-haiku-4-5)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL
    
    def analyze_item(
        self,
        content: str,
        role_description: str,
        item_title: str = "",
        category: str = ""
    ) -> Tuple[float, str, str]:
        """
        Analyze a bulletin item for relevance.
        
        Args:
            content: The bulletin item content
            role_description: User's role and interests
            item_title: Title of the item
            category: Category of the item
            
        Returns:
            Tuple of (score, explanation, short_title) where score is 0-100
        """
        prompt = self._build_analysis_prompt(
            content, role_description, item_title, category
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            return self._parse_response(response_text)
        
        except Exception as e:
            print(f"API Error: {e}")
            return 0.0, f"Error during analysis: {str(e)}", ""
    
    def _build_analysis_prompt(
        self,
        content: str,
        role_description: str,
        item_title: str,
        category: str
    ) -> str:
        """Build the prompt for relevance analysis."""
        return f"""You are analyzing a bulletin item from a university (JKU Linz, Austria) to determine if it's relevant for a specific person.

## THE PERSON'S ROLE AND INTERESTS:
{role_description}

## BULLETIN ITEM DETAILS:
Category: {category or "Not specified"}
Title: {item_title or "Not specified"}

## CONTENT:
{content[:50000]}

## YOUR TASK:
1. Analyze whether this bulletin item is relevant to the person based on their role and interests.
2. Provide a relevance score from 0 to 100:
   - 0-20: Not relevant at all
   - 21-40: Unlikely to be relevant
   - 41-60: Possibly relevant, might want to skim
   - 61-80: Likely relevant, should read
   - 81-100: Highly relevant, important to read

3. IMPORTANT: Err on the side of HIGHER scores. It's better to flag something as potentially relevant than to miss important information.
4. Create a short, descriptive title (5-7 words) that captures the essence of this bulletin item.

## RESPONSE FORMAT:
Respond in EXACTLY this format:

SCORE: [number 0-100]
SHORT_TITLE: [A concise 5-7 word title describing what this item is about]
SUMMARY: [1-2 sentences objectively describing WHAT this bulletin item contains - NO reasoning about relevance here]
RELEVANCE: [1-2 sentences explaining WHY this is or isn't relevant to this specific person]
KEY_POINTS: [If relevant, list 1-3 key points the person should know about]

Be concise. The person will use this to quickly filter through many bulletin items."""

    def _parse_response(self, response: str) -> Tuple[float, str, str]:
        """Parse the AI response into score, explanation, and short_title."""
        score = 0.0
        explanation = response
        short_title = ""
        
        # Extract score
        score_match = re.search(r'SCORE:\s*(\d+(?:\.\d+)?)', response, re.IGNORECASE)
        if score_match:
            score = min(100.0, max(0.0, float(score_match.group(1))))
        
        # Extract short title
        short_title_match = re.search(
            r'SHORT_TITLE:\s*(.+?)(?=SUMMARY:|EXPLANATION:|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if short_title_match:
            short_title = short_title_match.group(1).strip()[:200]
        
        # Extract summary (objective description)
        summary = ""
        summary_match = re.search(
            r'SUMMARY:\s*(.+?)(?=RELEVANCE:|EXPLANATION:|KEY_POINTS:|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if summary_match:
            summary = summary_match.group(1).strip()
        
        # Extract relevance explanation
        relevance = ""
        relevance_match = re.search(
            r'RELEVANCE:\s*(.+?)(?=KEY_POINTS:|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if relevance_match:
            relevance = relevance_match.group(1).strip()
        
        # Fallback: try old EXPLANATION format
        if not relevance:
            explanation_match = re.search(
                r'EXPLANATION:\s*(.+?)(?=KEY_POINTS:|$)',
                response,
                re.IGNORECASE | re.DOTALL
            )
            if explanation_match:
                relevance = explanation_match.group(1).strip()
        
        # Build the full explanation with clear separation
        parts = []
        if summary:
            parts.append(f"Summary: {summary}")
        if relevance:
            parts.append(f"Relevance: {relevance}")
        
        # Add key points if present
        key_points_match = re.search(
            r'KEY_POINTS:\s*(.+?)$',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if key_points_match:
            key_points = key_points_match.group(1).strip()
            if key_points and key_points.lower() not in ['none', 'n/a', '-']:
                parts.append(f"Key points: {key_points}")
        
        explanation = "\n\n".join(parts) if parts else response
        
        return score, explanation, short_title
    
    def batch_analyze(
        self,
        items: List[Dict],
        role_description: str
    ) -> List[Tuple[float, str, str]]:
        """
        Analyze multiple items efficiently.
        
        Args:
            items: List of dicts with content, title, category
            role_description: User's role and interests
            
        Returns:
            List of (score, explanation, short_title) tuples
        """
        results = []
        
        for item in items:
            score, explanation, short_title = self.analyze_item(
                content=item.get('content', ''),
                role_description=role_description,
                item_title=item.get('title', ''),
                category=item.get('category', '')
            )
            results.append((score, explanation, short_title))
        
        return results
    
    def analyze_with_pdf(
        self,
        content: str,
        pdf_text: str,
        role_description: str,
        item_title: str = "",
        category: str = ""
    ) -> str:
        """
        Analyze a bulletin item along with its PDF attachment content.
        
        Returns detailed analysis including PDF insights.
        """
        prompt = f"""You are analyzing a bulletin item from JKU Linz university, including its PDF attachment.

## THE PERSON'S ROLE AND INTERESTS:
{role_description}

## BULLETIN ITEM DETAILS:
Category: {category or "Not specified"}
Title: {item_title or "Not specified"}

## MAIN CONTENT:
{content[:20000]}

## PDF ATTACHMENT CONTENT:
{pdf_text[:30000]}

## YOUR TASK:
Provide a BRIEF analysis (keep it short and focused):

1. SUMMARY (2-3 sentences): What does the PDF contain?
2. KEY POINTS (3-5 bullet points max): Most important information from the PDF
3. RELEVANCE (1-2 sentences): Why this matters for this specific person

## IMPORTANT:
- Be concise - no more than 150 words total
- Use plain text only (no markdown headers or formatting symbols)
- Focus on the essential information
- Do NOT include action items or next steps"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
        
        except Exception as e:
            return f"Error during PDF analysis: {str(e)}"


class BulletinAnalyzer:
    """High-level analyzer that combines parsing and AI analysis."""
    
    def __init__(self, repository: Repository, config: dict):
        """
        Initialize with repository and configuration.
        
        Args:
            repository: Database repository instance
            config: Application configuration dict
        """
        self.repository = repository
        self.config = config
        
        api_key = config.get('anthropic_api_key')
        if not api_key:
            raise ValueError("anthropic_api_key is required in config")
        
        model = config.get('model', RelevanceAnalyzer.DEFAULT_MODEL)
        self.analyzer = RelevanceAnalyzer(api_key, model)
        
        self.role_description = config.get('role_description', '')
        if not self.role_description:
            raise ValueError("role_description is required in config")
        
        cache_dir = config.get('storage', {}).get('cache_dir', 'data/cache')
        self.pdf_parser = PDFParser(cache_dir)
        self.processor = ContentProcessor()
    
    def analyze_edition(self, edition: Edition, force: bool = False) -> Dict:
        """
        Analyze all items in an edition.
        
        Args:
            edition: Edition to analyze
            force: If True, re-analyze even if already analyzed
            
        Returns:
            Summary statistics dict
        """
        if edition.analyzed_at and not force:
            print(f"Edition {edition.edition_id} already analyzed. Use force=True to re-analyze.")
            return {'skipped': True}
        
        items = self.repository.get_items_for_edition(edition)
        if not items:
            print(f"No items found for edition {edition.edition_id}")
            return {'items': 0}
        
        print(f"Analyzing {len(items)} items from {edition.edition_id}...")
        
        results = {
            'items': len(items),
            'relevant': 0,
            'scores': [],
        }
        
        cache_dir = self.config.get('storage', {}).get('cache_dir', 'data/cache')
        
        for item in items:
            # Process content including attachments
            processed = process_bulletin_item(
                item.content or '',
                item.attachments,
                self.pdf_parser,
                cache_dir
            )
            
            # Analyze with AI
            score, explanation, short_title = self.analyzer.analyze_item(
                content=processed['combined_text'],
                role_description=self.role_description,
                item_title=item.title or '',
                category=item.category or ''
            )
            
            # Save results
            self.repository.update_item_analysis(item, score, explanation, short_title)
            
            results['scores'].append(score)
            if score >= self.config.get('relevance_threshold', 60):
                results['relevant'] += 1
            
            print(f"  Item {item.punkt}: {score:.0f}% relevant - {short_title}")
        
        # Mark edition as analyzed
        edition.analyzed_at = datetime.now()
        self.repository.update_edition(edition)
        
        results['avg_score'] = (
            sum(results['scores']) / len(results['scores'])
            if results['scores'] else 0
        )
        return results
    
    def analyze_unprocessed(self) -> Dict:
        """
        Analyze all editions that have been scraped but not analyzed.
        
        Returns:
            Summary statistics dict
        """
        editions = self.repository.get_unanalyzed_editions()
        
        if not editions:
            print("No unanalyzed editions found.")
            return {'editions': 0}
        
        print(f"Found {len(editions)} editions to analyze.")
        
        total_results = {
            'editions': len(editions),
            'items': 0,
            'relevant': 0,
        }
        
        for edition in editions:
            result = self.analyze_edition(edition)
            total_results['items'] += result.get('items', 0)
            total_results['relevant'] += result.get('relevant', 0)
        
        return total_results
    
    def quick_relevance_check(self, text: str) -> Tuple[float, str, str]:
        """
        Quick relevance check for a piece of text.
        
        Args:
            text: Content to check
            
        Returns:
            Tuple of (score, explanation, short_title)
        """
        return self.analyzer.analyze_item(
            content=text,
            role_description=self.role_description
        )
    
    def analyze_item_with_pdf(self, item: BulletinItem) -> str:
        """
        Perform deep analysis of an item including its PDF attachments.
        
        Downloads and extracts PDF text, then sends to Claude for analysis.
        
        Args:
            item: BulletinItem to analyze
            
        Returns:
            Analysis text
        """
        content = item.content or ''
        
        # Extract text from PDF attachments
        pdf_texts = []
        cache_dir = self.config.get('storage', {}).get('cache_dir', 'data/cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        for att in item.attachments:
            url = att.get('url', '')
            name = att.get('name', 'document.pdf')
            
            if not url:
                continue
            
            # Download PDF if not cached
            safe_name = "".join(
                c if c.isalnum() or c in '._-' else '_' for c in name
            )
            local_path = os.path.join(cache_dir, f"{item.id}_{safe_name}")
            
            try:
                if not os.path.exists(local_path):
                    print(f"Downloading: {name}")
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                
                # Extract text
                pdf_text = self.pdf_parser.extract_text(local_path)
                if pdf_text:
                    pdf_texts.append(f"=== {name} ===\n{pdf_text}")
            except Exception as e:
                print(f"Error processing PDF {name}: {e}")
                pdf_texts.append(f"=== {name} ===\n[Error extracting text: {e}]")
        
        # Combine all PDF texts
        combined_pdf_text = (
            "\n\n".join(pdf_texts)
            if pdf_texts
            else "No PDF attachments or could not extract text."
        )
        
        # Analyze with Claude
        analysis = self.analyzer.analyze_with_pdf(
            content=content,
            pdf_text=combined_pdf_text,
            role_description=self.role_description,
            item_title=item.title or '',
            category=item.category or ''
        )
        
        # Save to database
        self.repository.update_item_pdf_analysis(item, analysis)
        
        return analysis


def analyze_edition_cli(config: dict, edition_id: str, force: bool = False):
    """
    CLI-friendly function to analyze an edition.
    
    Args:
        config: Application configuration
        edition_id: Edition ID string (e.g., "2025-15")
        force: If True, re-analyze even if already analyzed
    """
    from ..db.repository import get_repository
    
    repository = get_repository(
        config.get('storage', {}).get('database', 'data/mtb.db')
    )
    analyzer = BulletinAnalyzer(repository, config)
    
    edition = repository.get_edition_by_id(edition_id)
    if not edition:
        print(f"Edition {edition_id} not found.")
        return
    
    result = analyzer.analyze_edition(edition, force=force)
    
    print(f"\nAnalysis complete:")
    print(f"  Items analyzed: {result.get('items', 0)}")
    print(f"  Relevant items: {result.get('relevant', 0)}")
    if result.get('avg_score'):
        print(f"  Average score: {result['avg_score']:.1f}%")


def analyze_all_cli(config: dict):
    """
    CLI-friendly function to analyze all unprocessed editions.
    
    Args:
        config: Application configuration
    """
    from ..db.repository import get_repository
    
    repository = get_repository(
        config.get('storage', {}).get('database', 'data/mtb.db')
    )
    analyzer = BulletinAnalyzer(repository, config)
    
    result = analyzer.analyze_unprocessed()
    
    print(f"\nBatch analysis complete:")
    print(f"  Editions processed: {result.get('editions', 0)}")
    print(f"  Total items: {result.get('items', 0)}")
    print(f"  Relevant items: {result.get('relevant', 0)}")
