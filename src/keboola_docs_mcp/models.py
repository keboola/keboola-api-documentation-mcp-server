"""Pydantic models for API documentation."""

from typing import Optional
from pydantic import BaseModel, Field


class Parameter(BaseModel):
    """API endpoint parameter."""

    name: str
    location: str = Field(description="path, query, header, or body")
    type: str = "string"
    required: bool = False
    description: str = ""
    default: Optional[str] = None
    example: Optional[str] = None


class Endpoint(BaseModel):
    """API endpoint documentation."""

    api_name: str = Field(description="Name of the API (e.g., 'Storage API')")
    section: str = Field(description="Section/group within the API (e.g., 'Tables')")
    path: str = Field(description="URL path (e.g., '/v2/storage/tables')")
    method: str = Field(description="HTTP method (GET, POST, PUT, DELETE, PATCH)")
    summary: str = Field(description="Brief summary of the endpoint")
    description: str = Field(default="", description="Full description")
    parameters: list[Parameter] = Field(default_factory=list)
    request_body_schema: Optional[dict] = Field(default=None, description="JSON schema for request body")
    request_example: Optional[str] = Field(default=None, description="Example request body")
    response_example: Optional[str] = Field(default=None, description="Example response")
    auth_header: Optional[str] = Field(default=None, description="Authentication header name")
    base_url: Optional[str] = Field(default=None, description="Base URL for the API")

    @property
    def key(self) -> str:
        """Unique key for this endpoint."""
        return f"{self.api_name}:{self.method}:{self.path}"

    @property
    def searchable_text(self) -> str:
        """Combined text for keyword matching."""
        parts = [
            self.api_name,
            self.section,
            self.path,
            self.method,
            self.summary,
            self.description,
        ]
        parts.extend(p.name for p in self.parameters)
        parts.extend(p.description for p in self.parameters)
        return " ".join(parts)


class ApiInfo(BaseModel):
    """Information about an API."""

    name: str
    description: str = ""
    base_url: Optional[str] = None
    auth_header: Optional[str] = None
    sections: list[str] = Field(default_factory=list)
    endpoint_count: int = 0


class DocumentSource(BaseModel):
    """Configuration for a documentation source."""

    name: str
    url: str
    output: str
    format: str = Field(description="apib or openapi")
    description: str = ""
    auth_header: Optional[str] = None
    base_url: Optional[str] = None


class SourcesConfig(BaseModel):
    """Configuration file structure for sources.yaml."""

    sources: list[DocumentSource]
