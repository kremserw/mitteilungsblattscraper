"""
Centralized configuration management for JKU MTB Analyzer.

Provides:
- Configuration loading from YAML files
- Schema validation
- Environment variable support
- Default values
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import yaml


@dataclass
class StorageConfig:
    """Database storage configuration."""
    database: str = "data/mtb.db"
    cache_dir: str = "data/cache"


@dataclass
class ScrapingConfig:
    """Web scraping configuration."""
    headless: bool = True
    delay_seconds: int = 2
    max_pages: int = 10


@dataclass
class AppConfig:
    """Main application configuration."""
    anthropic_api_key: str = ""
    model: str = "claude-haiku-4-5"
    role_description: str = ""
    relevance_threshold: float = 60.0
    storage: StorageConfig = field(default_factory=StorageConfig)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    _config_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backwards compatibility."""
        return {
            'anthropic_api_key': self.anthropic_api_key,
            'model': self.model,
            'role_description': self.role_description,
            'relevance_threshold': self.relevance_threshold,
            'storage': {
                'database': self.storage.database,
                'cache_dir': self.storage.cache_dir,
            },
            'scraping': {
                'headless': self.scraping.headless,
                'delay_seconds': self.scraping.delay_seconds,
                'max_pages': self.scraping.max_pages,
            },
            '_config_path': self._config_path,
        }


class ConfigError(Exception):
    """Configuration error."""
    pass


def load_config(
    config_path: str = "config.yaml",
    validate: bool = True
) -> Dict[str, Any]:
    """
    Load configuration from YAML file with environment variable support.
    
    Environment variables can override YAML values:
    - MTB_ANTHROPIC_API_KEY: Anthropic API key
    - MTB_DATABASE_PATH: Database file path
    - MTB_MODEL: Model to use for analysis
    
    Args:
        config_path: Path to YAML config file
        validate: Whether to validate required fields
        
    Returns:
        Configuration dictionary
        
    Raises:
        ConfigError: If config file not found or validation fails
    """
    # Check if config file exists
    if not os.path.exists(config_path):
        raise ConfigError(
            f"Config file not found: {config_path}\n"
            "Please copy config.example.yaml to config.yaml and fill in your details."
        )
    
    # Load YAML
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}
    
    # Apply environment variable overrides
    if os.getenv('MTB_ANTHROPIC_API_KEY'):
        config['anthropic_api_key'] = os.getenv('MTB_ANTHROPIC_API_KEY')
    
    if os.getenv('MTB_DATABASE_PATH'):
        if 'storage' not in config:
            config['storage'] = {}
        config['storage']['database'] = os.getenv('MTB_DATABASE_PATH')
    
    if os.getenv('MTB_MODEL'):
        config['model'] = os.getenv('MTB_MODEL')
    
    # Set defaults
    config.setdefault('model', 'claude-haiku-4-5')
    config.setdefault('relevance_threshold', 60.0)
    config.setdefault('storage', {})
    config['storage'].setdefault('database', 'data/mtb.db')
    config['storage'].setdefault('cache_dir', 'data/cache')
    config.setdefault('scraping', {})
    config['scraping'].setdefault('headless', True)
    config['scraping'].setdefault('delay_seconds', 2)
    
    # Store config path for later updates
    config['_config_path'] = config_path
    
    # Validate if requested
    if validate:
        validate_config(config)
    
    return config


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration has all required fields.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ConfigError: If validation fails
    """
    # Check API key
    api_key = config.get('anthropic_api_key', '')
    if not api_key:
        raise ConfigError("anthropic_api_key is required in config")
    if api_key.startswith('sk-ant-api03-your'):
        raise ConfigError(
            "Please replace the placeholder API key with your actual Anthropic API key"
        )
    
    # Check role description
    role_desc = config.get('role_description', '')
    if not role_desc:
        raise ConfigError("role_description is required in config")


def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> None:
    """
    Save configuration to YAML file.
    
    Only saves user-editable fields (not internal ones like _config_path).
    
    Args:
        config: Configuration dictionary
        config_path: Path to save to (uses config['_config_path'] if not provided)
    """
    path = config_path or config.get('_config_path', 'config.yaml')
    
    # Create a clean config dict without internal fields
    clean_config = {
        'anthropic_api_key': config.get('anthropic_api_key', ''),
        'model': config.get('model', 'claude-haiku-4-5'),
        'role_description': config.get('role_description', ''),
        'relevance_threshold': config.get('relevance_threshold', 60.0),
        'storage': config.get('storage', {}),
        'scraping': config.get('scraping', {}),
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(clean_config, f, default_flow_style=False, allow_unicode=True)


def get_db_path(config: Dict[str, Any]) -> str:
    """
    Get database path from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Database file path
    """
    return config.get('storage', {}).get('database', 'data/mtb.db')


def get_cache_dir(config: Dict[str, Any]) -> str:
    """
    Get cache directory from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Cache directory path
    """
    return config.get('storage', {}).get('cache_dir', 'data/cache')
