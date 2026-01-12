"""Documentation updater - fetches docs from online sources."""

import base64
import hashlib
import os
import re
from pathlib import Path
from typing import Optional

import httpx

from .config import get_project_root, load_sources
from .models import DocumentSource


class UpdateResult:
    """Result of updating a single source."""

    def __init__(
        self,
        source: DocumentSource,
        success: bool,
        updated: bool = False,
        error: Optional[str] = None,
    ):
        self.source = source
        self.success = success
        self.updated = updated
        self.error = error

    def __repr__(self) -> str:
        status = "updated" if self.updated else ("ok" if self.success else f"error: {self.error}")
        return f"UpdateResult({self.source.name}: {status})"


def get_file_hash(path: Path) -> Optional[str]:
    """Get MD5 hash of a file, or None if it doesn't exist."""
    if not path.exists():
        return None
    return hashlib.md5(path.read_bytes()).hexdigest()


def raw_url_to_api_url(raw_url: str) -> Optional[str]:
    """Convert raw.githubusercontent.com URL to GitHub API URL.

    Example:
        https://raw.githubusercontent.com/keboola/repo/main/path/file.txt
        -> https://api.github.com/repos/keboola/repo/contents/path/file.txt?ref=main
    """
    match = re.match(
        r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)",
        raw_url,
    )
    if match:
        owner, repo, ref, path = match.groups()
        return f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    return None


async def fetch_via_github_api(
    client: httpx.AsyncClient,
    api_url: str,
    token: Optional[str] = None,
) -> bytes:
    """Fetch file content via GitHub API.

    Returns the decoded file content.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    response = await client.get(api_url, headers=headers, follow_redirects=True)
    response.raise_for_status()

    data = response.json()
    if "content" in data:
        # Content is base64 encoded
        return base64.b64decode(data["content"])
    else:
        raise ValueError("No content in API response")


async def fetch_source(
    client: httpx.AsyncClient,
    source: DocumentSource,
    output_dir: Path,
    dry_run: bool = False,
    github_token: Optional[str] = None,
) -> UpdateResult:
    """Fetch a single documentation source.

    Args:
        client: HTTP client to use
        source: Source configuration
        output_dir: Base directory for output files
        dry_run: If True, don't write files, just check
        github_token: GitHub token for private repos

    Returns:
        UpdateResult with status
    """
    output_path = output_dir / source.output

    try:
        # Try raw URL first
        try:
            response = await client.get(source.url, follow_redirects=True)
            response.raise_for_status()
            content = response.content
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Try GitHub API as fallback (for private repos)
                api_url = raw_url_to_api_url(source.url)
                if api_url and github_token:
                    content = await fetch_via_github_api(client, api_url, github_token)
                else:
                    raise
            else:
                raise

        # Check if content changed
        old_hash = get_file_hash(output_path)
        new_hash = hashlib.md5(content).hexdigest()

        if old_hash == new_hash:
            return UpdateResult(source, success=True, updated=False)

        if dry_run:
            return UpdateResult(source, success=True, updated=True)

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        output_path.write_bytes(content)

        return UpdateResult(source, success=True, updated=True)

    except httpx.HTTPStatusError as e:
        return UpdateResult(source, success=False, error=f"HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        return UpdateResult(source, success=False, error=str(e))
    except Exception as e:
        return UpdateResult(source, success=False, error=str(e))


async def update_docs(
    sources_file: Optional[Path] = None,
    api_filter: Optional[str] = None,
    dry_run: bool = False,
) -> list[UpdateResult]:
    """Update all documentation from online sources.

    Args:
        sources_file: Path to sources.yaml (default: project root)
        api_filter: If provided, only update sources matching this name
        dry_run: If True, don't write files, just check for updates

    Returns:
        List of UpdateResult for each source
    """
    sources = load_sources(sources_file)
    output_dir = get_project_root()

    # Get GitHub token from environment
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    # Filter sources if requested
    if api_filter:
        api_filter_lower = api_filter.lower()
        sources = [s for s in sources if api_filter_lower in s.name.lower()]

    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for source in sources:
            result = await fetch_source(client, source, output_dir, dry_run, github_token)
            results.append(result)

    return results


def update_docs_sync(
    sources_file: Optional[Path] = None,
    api_filter: Optional[str] = None,
    dry_run: bool = False,
) -> list[UpdateResult]:
    """Synchronous wrapper for update_docs."""
    import asyncio

    return asyncio.run(update_docs(sources_file, api_filter, dry_run))
