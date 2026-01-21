"""
AI Analyzer for JKU MTB content.
Uses Claude Haiku for relevance scoring.
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import anthropic

from .storage import Storage, BulletinItem, Edition
from .parser import PDFParser, ContentProcessor, process_bulletin_item


class RelevanceAnalyzer:
    """Analyzes bulletin content for relevance using Claude Haiku."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        """Initialize with Anthropic API key."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def analyze_item(
        self,
        content: str,
        role_description: str,
        item_title: str = "",
        category: str = ""
    ) -> Tuple[float, str]:
        """
        Analyze a bulletin item for relevance.
        
        Returns (score, explanation) where score is 0-100.
        """
        prompt = self._build_analysis_prompt(content, role_description, item_title, category)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = response.content[0].text
            return self._parse_response(response_text)
        
        except Exception as e:
            print(f"API Error: {e}")
            return 0.0, f"Error during analysis: {str(e)}"
    
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
{content[:50000]}  <!-- Truncated for safety -->

## YOUR TASK:
1. Analyze whether this bulletin item is relevant to the person based on their role and interests.
2. Provide a relevance score from 0 to 100:
   - 0-20: Not relevant at all
   - 21-40: Unlikely to be relevant
   - 41-60: Possibly relevant, might want to skim
   - 61-80: Likely relevant, should read
   - 81-100: Highly relevant, important to read

3. IMPORTANT: Err on the side of HIGHER scores. It's better to flag something as potentially relevant than to miss important information.

## RESPONSE FORMAT:
Respond in EXACTLY this format:

SCORE: [number 0-100]
EXPLANATION: [Brief explanation in 1-3 sentences of why this is or isn't relevant]
KEY_POINTS: [If relevant, list 1-3 key points the person should know about]

Be concise. The person will use this to quickly filter through many bulletin items."""

    def _parse_response(self, response: str) -> Tuple[float, str]:
        """Parse the AI response into score and explanation."""
        score = 0.0
        explanation = response
        
        # Extract score
        score_match = re.search(r'SCORE:\s*(\d+(?:\.\d+)?)', response, re.IGNORECASE)
        if score_match:
            score = min(100.0, max(0.0, float(score_match.group(1))))
        
        # Extract explanation
        explanation_match = re.search(
            r'EXPLANATION:\s*(.+?)(?=KEY_POINTS:|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if explanation_match:
            explanation = explanation_match.group(1).strip()
        
        # Add key points if present
        key_points_match = re.search(
            r'KEY_POINTS:\s*(.+?)$',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if key_points_match:
            key_points = key_points_match.group(1).strip()
            if key_points and key_points.lower() not in ['none', 'n/a', '-']:
                explanation += f"\n\nKey points: {key_points}"
        
        return score, explanation
    
    def batch_analyze(
        self,
        items: List[Dict],
        role_description: str
    ) -> List[Tuple[float, str]]:
        """
        Analyze multiple items efficiently.
        
        Each item should have: content, title, category
        """
        results = []
        
        for item in items:
            score, explanation = self.analyze_item(
                content=item.get('content', ''),
                role_description=role_description,
                item_title=item.get('title', ''),
                category=item.get('category', '')
            )
            results.append((score, explanation))
        
        return results


class BulletinAnalyzer:
    """High-level analyzer that combines scraping, parsing, and AI analysis."""
    
    def __init__(self, storage: Storage, config: dict):
        """Initialize with storage and configuration."""
        self.storage = storage
        self.config = config
        
        api_key = config.get('anthropic_api_key')
        if not api_key:
            raise ValueError("anthropic_api_key is required in config")
        
        model = config.get('model', 'claude-3-5-haiku-20241022')
        self.analyzer = RelevanceAnalyzer(api_key, model)
        
        self.role_description = config.get('role_description', '')
        if not self.role_description:
            raise ValueError("role_description is required in config")
        
        self.pdf_parser = PDFParser(config.get('storage', {}).get('cache_dir', 'data/cache'))
        self.processor = ContentProcessor()
    
    def analyze_edition(self, edition: Edition, force: bool = False) -> Dict:
        """
        Analyze all items in an edition.
        
        Returns summary statistics.
        """
        if edition.analyzed_at and not force:
            print(f"Edition {edition.edition_id} already analyzed. Use force=True to re-analyze.")
            return {'skipped': True}
        
        items = self.storage.get_items_for_edition(edition)
        if not items:
            print(f"No items found for edition {edition.edition_id}")
            return {'items': 0}
        
        print(f"Analyzing {len(items)} items from {edition.edition_id}...")
        
        results = {
            'items': len(items),
            'relevant': 0,
            'scores': [],
        }
        
        for item in items:
            # Process content including attachments
            processed = process_bulletin_item(
                item.content or '',
                item.attachments,
                self.pdf_parser,
                self.config.get('storage', {}).get('cache_dir', 'data/cache')
            )
            
            # Analyze with AI
            score, explanation = self.analyzer.analyze_item(
                content=processed['combined_text'],
                role_description=self.role_description,
                item_title=item.title or '',
                category=item.category or ''
            )
            
            # Save results
            self.storage.update_item_analysis(item, score, explanation)
            
            results['scores'].append(score)
            if score >= self.config.get('relevance_threshold', 60):
                results['relevant'] += 1
            
            print(f"  Item {item.punkt}: {score:.0f}% relevant")
        
        # Mark edition as analyzed
        edition.analyzed_at = datetime.now()
        self.storage.update_edition(edition)
        
        results['avg_score'] = sum(results['scores']) / len(results['scores']) if results['scores'] else 0
        return results
    
    def analyze_unprocessed(self) -> Dict:
        """Analyze all editions that have been scraped but not analyzed."""
        editions = self.storage.get_unanalyzed_editions()
        
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
    
    def quick_relevance_check(self, text: str) -> Tuple[float, str]:
        """
        Quick relevance check for a piece of text.
        Useful for checking individual items without full processing.
        """
        return self.analyzer.analyze_item(
            content=text,
            role_description=self.role_description
        )


def analyze_edition_cli(config: dict, edition_id: str, force: bool = False):
    """CLI-friendly function to analyze an edition."""
    from .storage import get_storage
    
    storage = get_storage(config.get('storage', {}).get('database', 'data/mtb.db'))
    analyzer = BulletinAnalyzer(storage, config)
    
    edition = storage.get_edition_by_id(edition_id)
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
    """CLI-friendly function to analyze all unprocessed editions."""
    from .storage import get_storage
    
    storage = get_storage(config.get('storage', {}).get('database', 'data/mtb.db'))
    analyzer = BulletinAnalyzer(storage, config)
    
    result = analyzer.analyze_unprocessed()
    
    print(f"\nBatch analysis complete:")
    print(f"  Editions processed: {result.get('editions', 0)}")
    print(f"  Total items: {result.get('items', 0)}")
    print(f"  Relevant items: {result.get('relevant', 0)}")
