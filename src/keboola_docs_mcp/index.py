"""Search index for API documentation."""

import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from .config import get_docs_dir, load_sources
from .models import ApiInfo, DocumentSource, Endpoint
from .parsers import ApibParser, OpenApiParser


# Stopwords to exclude from indexing
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "you", "your", "we", "our", "api", "endpoint", "request", "response",
}


class SearchIndex:
    """Inverted index for searching endpoints."""

    def __init__(self):
        self.endpoints: dict[str, Endpoint] = {}
        self.inverted_index: dict[str, set[str]] = defaultdict(set)
        self.api_info: dict[str, ApiInfo] = {}
        self.api_sections: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    def add_endpoint(self, endpoint: Endpoint) -> None:
        """Add an endpoint to the index."""
        key = endpoint.key
        self.endpoints[key] = endpoint

        # Tokenize and index
        tokens = self._tokenize(endpoint.searchable_text)
        for token in tokens:
            self.inverted_index[token].add(key)

        # Add to API sections
        self.api_sections[endpoint.api_name][endpoint.section].append(key)

        # Update API info
        if endpoint.api_name not in self.api_info:
            self.api_info[endpoint.api_name] = ApiInfo(
                name=endpoint.api_name,
                base_url=endpoint.base_url,
                auth_header=endpoint.auth_header,
            )
        api_info = self.api_info[endpoint.api_name]
        api_info.endpoint_count += 1
        if endpoint.section not in api_info.sections:
            api_info.sections.append(endpoint.section)

    def search(
        self,
        query: str,
        api_filter: Optional[str] = None,
        method_filter: Optional[str] = None,
        limit: int = 10,
    ) -> list[Endpoint]:
        """Search for endpoints matching a query.

        Args:
            query: Search query string
            api_filter: Filter by API name (substring match)
            method_filter: Filter by HTTP method
            limit: Maximum number of results

        Returns:
            List of matching endpoints, sorted by relevance
        """
        tokens = self._tokenize(query)

        if not tokens:
            return []

        # Score by token matches
        scores: dict[str, float] = defaultdict(float)

        for token in tokens:
            for key in self.inverted_index.get(token, []):
                endpoint = self.endpoints[key]

                # Apply filters
                if api_filter and api_filter.lower() not in endpoint.api_name.lower():
                    continue
                if method_filter and endpoint.method.upper() != method_filter.upper():
                    continue

                # Score boost for exact matches in path or summary
                base_score = 1.0
                if token in endpoint.path.lower():
                    base_score += 2.0
                if token in endpoint.summary.lower():
                    base_score += 1.5
                if token in endpoint.section.lower():
                    base_score += 1.0

                scores[key] += base_score

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:limit]
        return [self.endpoints[key] for key, _ in ranked]

    def get_endpoint(
        self,
        api_name: str,
        path: str,
        method: str,
    ) -> Optional[Endpoint]:
        """Get a specific endpoint by API name, path, and method.

        Args:
            api_name: Name of the API
            path: URL path
            method: HTTP method

        Returns:
            Endpoint if found, None otherwise
        """
        key = f"{api_name}:{method.upper()}:{path}"
        return self.endpoints.get(key)

    def get_api_endpoints(
        self,
        api_name: str,
        section: Optional[str] = None,
    ) -> list[Endpoint]:
        """Get all endpoints for an API or section.

        Args:
            api_name: Name of the API
            section: Optional section to filter by

        Returns:
            List of endpoints
        """
        if api_name not in self.api_sections:
            return []

        sections = self.api_sections[api_name]

        if section:
            # Find section by substring match
            matching_section = None
            for s in sections:
                if section.lower() in s.lower():
                    matching_section = s
                    break
            if not matching_section:
                return []
            keys = sections[matching_section]
        else:
            # All sections
            keys = []
            for section_keys in sections.values():
                keys.extend(section_keys)

        return [self.endpoints[key] for key in keys if key in self.endpoints]

    def list_apis(self) -> list[ApiInfo]:
        """List all available APIs."""
        return list(self.api_info.values())

    def list_sections(self, api_name: str) -> list[str]:
        """List all sections for an API."""
        if api_name not in self.api_sections:
            return []
        return list(self.api_sections[api_name].keys())

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text for indexing/searching."""
        # Lowercase and split on non-alphanumeric
        words = re.findall(r"[a-z0-9]+", text.lower())
        # Remove stopwords and short words
        return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def build_index(sources_file: Optional[Path] = None) -> SearchIndex:
    """Build search index from all documentation sources.

    Args:
        sources_file: Path to sources.yaml (default: project root)

    Returns:
        SearchIndex populated with endpoints from all sources
    """
    sources = load_sources(sources_file)
    docs_dir = get_docs_dir()
    index = SearchIndex()

    for source in sources:
        file_path = docs_dir.parent / source.output

        if not file_path.exists():
            continue

        try:
            if source.format == "apib":
                endpoints = ApibParser.parse_file(
                    file_path,
                    api_name=source.name,
                    auth_header=source.auth_header,
                    base_url=source.base_url,
                )
            elif source.format == "openapi":
                endpoints = OpenApiParser.parse_file(
                    file_path,
                    api_name=source.name,
                    auth_header=source.auth_header,
                    base_url=source.base_url,
                )
            else:
                continue

            for endpoint in endpoints:
                index.add_endpoint(endpoint)

            # Update API description
            if source.name in index.api_info:
                index.api_info[source.name].description = source.description

        except Exception as e:
            # Log error but continue with other sources
            print(f"Warning: Failed to parse {source.name}: {e}")

    return index
