"""Configuration management for Scriptor Local."""
import os
import json
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# Default paths
DEFAULT_CONFIG_DIR = Path.home() / ".scriptor"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


class Config:
    """Application configuration loaded from JSON file."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_FILE):
        self.config_path = config_path
        self._ensure_config_exists()
        self._load()

    def _ensure_config_exists(self):
        """Create default config if it doesn't exist."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():
            default_storage = self.config_path.parent / "storage"
            default_config = {
                "storage_dir": str(default_storage),
                "auth_token": secrets.token_urlsafe(32),
                "server_port": 52525,
                "gemini_api_key": "",
                "pix2tex_enabled": False,
                "embedding_model": "all-MiniLM-L6-v2",
                "auto_start_server": True
            }

            # Create storage directories
            for subdir in ["PDFs", "Exports", "Models", "DB"]:
                (default_storage / subdir).mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)

    def _load(self):
        """Load configuration from file."""
        with open(self.config_path, 'r') as f:
            data = json.load(f)

        self.storage_dir = Path(data.get("storage_dir", str(DEFAULT_CONFIG_DIR / "storage")))
        self.auth_token = data.get("auth_token", secrets.token_urlsafe(32))
        self.server_port = data.get("server_port", 52525)
        self.gemini_api_key = data.get("gemini_api_key", "")
        self.pix2tex_enabled = data.get("pix2tex_enabled", False)
        self.embedding_model = data.get("embedding_model", "all-MiniLM-L6-v2")
        self.auto_start_server = data.get("auto_start_server", True)

        # Derived paths
        self.pdfs_dir = self.storage_dir / "PDFs"
        self.exports_dir = self.storage_dir / "Exports"
        self.models_dir = self.storage_dir / "Models"
        self.db_dir = self.storage_dir / "DB"
        self.db_path = self.db_dir / "scriptor.db"

        # Ensure directories exist
        for dir_path in [self.pdfs_dir, self.exports_dir, self.models_dir, self.db_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def save(self):
        """Save current configuration to file."""
        data = {
            "storage_dir": str(self.storage_dir),
            "auth_token": self.auth_token,
            "server_port": self.server_port,
            "gemini_api_key": self.gemini_api_key,
            "pix2tex_enabled": self.pix2tex_enabled,
            "embedding_model": self.embedding_model,
            "auto_start_server": self.auto_start_server
        }
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def regenerate_token(self) -> str:
        """Generate a new auth token."""
        self.auth_token = secrets.token_urlsafe(32)
        self.save()
        return self.auth_token

    def set_storage_dir(self, path: str):
        """Update storage directory."""
        new_storage = Path(path)
        for subdir in ["PDFs", "Exports", "Models", "DB"]:
            (new_storage / subdir).mkdir(parents=True, exist_ok=True)
        self.storage_dir = new_storage
        self._load()  # Reload derived paths
        self.save()


# Global config instance
config = Config()
