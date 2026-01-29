"""
PDF download proxy service.

Provides server-side PDF downloads to handle CORS and filename issues.
"""

import html
from typing import Generator, Tuple, Optional

import requests


def download_pdf(
    url: str,
    timeout: int = 30
) -> Tuple[Generator[bytes, None, None], str, Optional[str]]:
    """
    Download a PDF from a URL.
    
    Args:
        url: URL to download from
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (content_iterator, content_type, error)
        If error is not None, the download failed
    """
    # Decode HTML entities in URL
    url = html.unescape(url)
    
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', 'application/pdf')
        
        return (
            response.iter_content(chunk_size=8192),
            content_type,
            None
        )
    except requests.RequestException as e:
        return (iter([]), 'application/octet-stream', str(e))
