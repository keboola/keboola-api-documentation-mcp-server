"""Tests for search index."""

import pytest

from keboola_docs_mcp.index import SearchIndex, build_index
from keboola_docs_mcp.models import Endpoint, Parameter


class TestSearchIndex:
    """Tests for SearchIndex."""

    def test_add_and_search_endpoint(self):
        """Test adding and searching for endpoints."""
        index = SearchIndex()

        endpoint = Endpoint(
            api_name="Test API",
            section="Users",
            path="/users",
            method="GET",
            summary="List all users",
            description="Returns a list of all users in the system",
            parameters=[],
        )
        index.add_endpoint(endpoint)

        results = index.search("users")
        assert len(results) == 1
        assert results[0].path == "/users"

    def test_search_by_path(self):
        """Test searching by path components."""
        index = SearchIndex()

        index.add_endpoint(Endpoint(
            api_name="Storage API",
            section="Tables",
            path="/v2/storage/tables",
            method="GET",
            summary="List tables",
        ))
        index.add_endpoint(Endpoint(
            api_name="Storage API",
            section="Buckets",
            path="/v2/storage/buckets",
            method="GET",
            summary="List buckets",
        ))

        results = index.search("tables")
        assert len(results) == 1
        assert results[0].path == "/v2/storage/tables"

    def test_search_with_api_filter(self):
        """Test filtering by API name."""
        index = SearchIndex()

        index.add_endpoint(Endpoint(
            api_name="Storage API",
            section="Tables",
            path="/tables",
            method="GET",
            summary="List tables",
        ))
        index.add_endpoint(Endpoint(
            api_name="Management API",
            section="Projects",
            path="/projects",
            method="GET",
            summary="List projects",
        ))

        results = index.search("list", api_filter="storage")
        assert len(results) == 1
        assert results[0].api_name == "Storage API"

    def test_search_with_method_filter(self):
        """Test filtering by HTTP method."""
        index = SearchIndex()

        index.add_endpoint(Endpoint(
            api_name="API",
            section="Resources",
            path="/resources",
            method="GET",
            summary="Get resources",
        ))
        index.add_endpoint(Endpoint(
            api_name="API",
            section="Resources",
            path="/resources",
            method="POST",
            summary="Create resource",
        ))

        results = index.search("resources", method_filter="POST")
        assert len(results) == 1
        assert results[0].method == "POST"

    def test_get_endpoint(self):
        """Test getting a specific endpoint."""
        index = SearchIndex()

        endpoint = Endpoint(
            api_name="Test API",
            section="Test",
            path="/test",
            method="GET",
            summary="Test endpoint",
        )
        index.add_endpoint(endpoint)

        result = index.get_endpoint("Test API", "/test", "GET")
        assert result is not None
        assert result.summary == "Test endpoint"

        result = index.get_endpoint("Test API", "/test", "POST")
        assert result is None

    def test_list_apis(self):
        """Test listing all APIs."""
        index = SearchIndex()

        index.add_endpoint(Endpoint(
            api_name="API 1",
            section="Section",
            path="/path1",
            method="GET",
            summary="Test 1",
        ))
        index.add_endpoint(Endpoint(
            api_name="API 2",
            section="Section",
            path="/path2",
            method="GET",
            summary="Test 2",
        ))

        apis = index.list_apis()
        assert len(apis) == 2
        api_names = {api.name for api in apis}
        assert "API 1" in api_names
        assert "API 2" in api_names

    def test_get_api_section(self):
        """Test getting endpoints by section."""
        index = SearchIndex()

        index.add_endpoint(Endpoint(
            api_name="API",
            section="Tables",
            path="/tables",
            method="GET",
            summary="List tables",
        ))
        index.add_endpoint(Endpoint(
            api_name="API",
            section="Tables",
            path="/tables",
            method="POST",
            summary="Create table",
        ))
        index.add_endpoint(Endpoint(
            api_name="API",
            section="Buckets",
            path="/buckets",
            method="GET",
            summary="List buckets",
        ))

        results = index.get_api_endpoints("API", "Tables")
        assert len(results) == 2
        assert all(ep.section == "Tables" for ep in results)


class TestBuildIndex:
    """Tests for build_index function."""

    def test_build_index_from_docs(self):
        """Test building index from documentation files."""
        index = build_index()

        # Should have multiple APIs
        apis = index.list_apis()
        assert len(apis) > 0

        # Should have endpoints
        assert len(index.endpoints) > 0

        # Storage API should be present if docs exist
        storage_endpoints = index.get_api_endpoints("Storage API")
        if storage_endpoints:
            assert len(storage_endpoints) > 0
