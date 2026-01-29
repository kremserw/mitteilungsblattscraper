"""Unit tests for configuration module."""

import os
import tempfile

import pytest
import yaml

from src.config import load_config, validate_config, ConfigError, get_db_path


class TestConfigLoading:
    """Tests for configuration loading."""
    
    def test_load_config_valid(self):
        """Test loading a valid config file."""
        # Create a temporary config file
        config_data = {
            'anthropic_api_key': 'sk-ant-api03-valid-key',
            'role_description': 'Test role description',
            'model': 'claude-haiku-4-5',
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            
            assert config['anthropic_api_key'] == 'sk-ant-api03-valid-key'
            assert config['role_description'] == 'Test role description'
            assert config['model'] == 'claude-haiku-4-5'
            assert config['_config_path'] == temp_path
        finally:
            os.unlink(temp_path)
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent config file raises error."""
        with pytest.raises(ConfigError) as exc_info:
            load_config('/nonexistent/config.yaml')
        
        assert 'not found' in str(exc_info.value)
    
    def test_load_config_defaults(self):
        """Test that defaults are applied."""
        config_data = {
            'anthropic_api_key': 'sk-ant-api03-valid-key',
            'role_description': 'Test role',
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            
            # Check defaults are applied
            assert config['model'] == 'claude-haiku-4-5'
            assert config['relevance_threshold'] == 60.0
            assert config['storage']['database'] == 'data/mtb.db'
            assert config['storage']['cache_dir'] == 'data/cache'
            assert config['scraping']['headless'] is True
        finally:
            os.unlink(temp_path)
    
    def test_load_config_env_override(self, monkeypatch):
        """Test that environment variables override config values."""
        config_data = {
            'anthropic_api_key': 'sk-ant-api03-from-file',
            'role_description': 'Test role',
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # Set environment variable
            monkeypatch.setenv('MTB_ANTHROPIC_API_KEY', 'sk-ant-api03-from-env')
            
            config = load_config(temp_path)
            
            # Environment variable should override
            assert config['anthropic_api_key'] == 'sk-ant-api03-from-env'
        finally:
            os.unlink(temp_path)


class TestConfigValidation:
    """Tests for configuration validation."""
    
    def test_validate_valid_config(self):
        """Test validating a valid configuration."""
        config = {
            'anthropic_api_key': 'sk-ant-api03-valid-key',
            'role_description': 'Test role description',
        }
        
        # Should not raise
        validate_config(config)
    
    def test_validate_missing_api_key(self):
        """Test validation fails without API key."""
        config = {
            'role_description': 'Test role',
        }
        
        with pytest.raises(ConfigError) as exc_info:
            validate_config(config)
        
        assert 'anthropic_api_key' in str(exc_info.value)
    
    def test_validate_placeholder_api_key(self):
        """Test validation fails with placeholder API key."""
        config = {
            'anthropic_api_key': 'sk-ant-api03-your-key-here',
            'role_description': 'Test role',
        }
        
        with pytest.raises(ConfigError) as exc_info:
            validate_config(config)
        
        assert 'placeholder' in str(exc_info.value).lower()
    
    def test_validate_missing_role_description(self):
        """Test validation fails without role description."""
        config = {
            'anthropic_api_key': 'sk-ant-api03-valid-key',
        }
        
        with pytest.raises(ConfigError) as exc_info:
            validate_config(config)
        
        assert 'role_description' in str(exc_info.value)


class TestConfigHelpers:
    """Tests for configuration helper functions."""
    
    def test_get_db_path(self):
        """Test getting database path from config."""
        config = {
            'storage': {
                'database': 'custom/path/db.sqlite',
            }
        }
        
        assert get_db_path(config) == 'custom/path/db.sqlite'
    
    def test_get_db_path_default(self):
        """Test getting default database path."""
        config = {}
        
        assert get_db_path(config) == 'data/mtb.db'
