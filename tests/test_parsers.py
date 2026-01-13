"""Tests for API documentation parsers."""

import pytest

from keboola_docs_mcp.parsers import ApibParser, OpenApiParser
from keboola_docs_mcp.config import get_docs_dir


class TestApibParser:
    """Tests for API Blueprint parser."""

    def test_parse_storage_api(self):
        """Test parsing Storage API documentation."""
        docs_dir = get_docs_dir()
        file_path = docs_dir / "apiary" / "storage-api.apib"

        if not file_path.exists():
            pytest.skip("Storage API docs not found")

        endpoints = ApibParser.parse_file(
            file_path,
            api_name="Storage API",
            auth_header="X-StorageApi-Token",
            base_url="https://connection.keboola.com",
        )

        assert len(endpoints) > 0
        assert any(ep.path.startswith("/v2/storage") for ep in endpoints)
        assert all(ep.api_name == "Storage API" for ep in endpoints)

    def test_parse_manages_groups(self):
        """Test that parser correctly identifies groups/sections."""
        content = """FORMAT: 1A
HOST: https://example.com

# Test API

## Introduction
Some intro text.

# Group Users

## User Collection [/users]

### List Users [GET]
Get all users.

+ Response 200 (application/json)

# Group Products

## Product [/products/{id}]

### Get Product [GET]
Get a product.

+ Parameters
    + id (required, number) - Product ID

+ Response 200 (application/json)
"""
        parser = ApibParser("Test API")
        endpoints = parser.parse(content)

        assert len(endpoints) == 2
        sections = {ep.section for ep in endpoints}
        assert "Users" in sections
        assert "Products" in sections

    def test_parse_extracts_parameters(self):
        """Test that parameters are correctly extracted."""
        content = """FORMAT: 1A

# Test API

# Group Test

## Resource [/test/{id}]

### Get [GET]

+ Parameters
    + id (required, number) - Resource ID

+ Response 200
"""
        parser = ApibParser("Test API")
        endpoints = parser.parse(content)

        assert len(endpoints) == 1
        assert len(endpoints[0].parameters) == 1
        assert endpoints[0].parameters[0].name == "id"
        assert endpoints[0].parameters[0].required is True


class TestOpenApiParser:
    """Tests for OpenAPI parser."""

    def test_parse_stream_service(self):
        """Test parsing Stream Service OpenAPI spec."""
        docs_dir = get_docs_dir()
        file_path = docs_dir / "openapi" / "stream-service.yaml"

        if not file_path.exists():
            pytest.skip("Stream Service docs not found")

        endpoints = OpenApiParser.parse_file(
            file_path,
            api_name="Stream Service",
        )

        assert len(endpoints) > 0
        assert all(ep.api_name == "Stream Service" for ep in endpoints)

    def test_parse_json_spec(self):
        """Test parsing JSON OpenAPI spec."""
        docs_dir = get_docs_dir()
        file_path = docs_dir / "openapi" / "query-service.json"

        if not file_path.exists():
            pytest.skip("Query Service docs not found")

        endpoints = OpenApiParser.parse_file(
            file_path,
            api_name="Query Service",
        )

        assert len(endpoints) > 0

    def test_parse_extracts_tags_as_sections(self):
        """Test that OpenAPI tags become sections."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/users": {
                    "get": {
                        "tags": ["Users"],
                        "summary": "List users",
                        "responses": {"200": {"description": "OK"}},
                    }
                },
                "/products": {
                    "get": {
                        "tags": ["Products"],
                        "summary": "List products",
                        "responses": {"200": {"description": "OK"}},
                    }
                },
            },
        }

        parser = OpenApiParser("Test API")
        endpoints = parser.parse(spec)

        assert len(endpoints) == 2
        sections = {ep.section for ep in endpoints}
        assert "Users" in sections
        assert "Products" in sections
