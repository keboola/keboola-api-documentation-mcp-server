"""Configuration for the Keboola docs MCP server."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic_settings import BaseSettings

from .models import DocumentSource, SourcesConfig


class Settings(BaseSettings):
    """Application settings."""

    # Path to sources.yaml
    sources_file: Path = Path("sources.yaml")

    # Path to docs directory
    docs_dir: Path = Path("docs")

    model_config = {"env_prefix": "KEBOOLA_DOCS_"}


def get_project_root() -> Path:
    """Get the project root directory."""
    # Start from the current file and go up to find pyproject.toml
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # Fallback to current working directory
    return Path.cwd()


def load_sources(sources_file: Optional[Path] = None) -> list[DocumentSource]:
    """Load documentation sources from YAML file."""
    if sources_file is None:
        sources_file = get_project_root() / "sources.yaml"

    if not sources_file.exists():
        raise FileNotFoundError(f"Sources file not found: {sources_file}")

    with open(sources_file) as f:
        data = yaml.safe_load(f)

    config = SourcesConfig(**data)
    return config.sources


def get_docs_dir() -> Path:
    """Get the docs directory path."""
    return get_project_root() / "docs"
