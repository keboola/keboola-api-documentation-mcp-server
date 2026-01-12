"""MCP server for Keboola API documentation."""

from contextlib import asynccontextmanager
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP

from .index import SearchIndex, build_index
from .models import ApiInfo, Endpoint


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initialize the search index at startup."""
    print("Building documentation index...")
    index = build_index()
    print(f"Indexed {len(index.endpoints)} endpoints from {len(index.api_info)} APIs")
    yield {"index": index}


# Create the MCP server
mcp = FastMCP(
    "Keboola API Documentation",
    lifespan=lifespan,
)


def get_index(ctx: Context) -> SearchIndex:
    """Get the search index from context."""
    return ctx.request_context.lifespan_context["index"]


@mcp.tool()
async def list_apis(ctx: Context) -> list[dict]:
    """List all available Keboola APIs.

    Returns a list of APIs with their names, descriptions, and endpoint counts.
    """
    index = get_index(ctx)
    apis = index.list_apis()
    return [
        {
            "name": api.name,
            "description": api.description,
            "base_url": api.base_url,
            "auth_header": api.auth_header,
            "sections": api.sections,
            "endpoint_count": api.endpoint_count,
        }
        for api in apis
    ]


@mcp.tool()
async def search_endpoints(
    ctx: Context,
    query: str,
    api_filter: Optional[str] = None,
    method_filter: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Search for API endpoints by keyword.

    Args:
        query: Search query (e.g., "create table", "upload file", "token")
        api_filter: Filter by API name (e.g., "Storage" to only search Storage API)
        method_filter: Filter by HTTP method (GET, POST, PUT, DELETE, PATCH)
        limit: Maximum number of results (default: 10)

    Returns a list of matching endpoints with their details.
    """
    index = get_index(ctx)
    endpoints = index.search(query, api_filter, method_filter, limit)
    return [_endpoint_to_dict(ep, brief=True) for ep in endpoints]


@mcp.tool()
async def get_endpoint_details(
    ctx: Context,
    api_name: str,
    path: str,
    method: str,
) -> Optional[dict]:
    """Get full details for a specific API endpoint.

    Args:
        api_name: Name of the API (e.g., "Storage API")
        path: URL path (e.g., "/v2/storage/tables")
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)

    Returns the endpoint details including parameters, request/response examples.
    """
    index = get_index(ctx)
    endpoint = index.get_endpoint(api_name, path, method)
    if endpoint:
        return _endpoint_to_dict(endpoint, brief=False)
    return None


@mcp.tool()
async def get_api_section(
    ctx: Context,
    api_name: str,
    section_name: Optional[str] = None,
) -> list[dict]:
    """Get all endpoints in an API section.

    Args:
        api_name: Name of the API (e.g., "Storage API")
        section_name: Section name (e.g., "Tables", "Buckets"). If not provided, returns all endpoints.

    Returns a list of endpoints in the section.
    """
    index = get_index(ctx)
    endpoints = index.get_api_endpoints(api_name, section_name)
    return [_endpoint_to_dict(ep, brief=True) for ep in endpoints]


@mcp.tool()
async def list_sections(
    ctx: Context,
    api_name: str,
) -> list[str]:
    """List all sections in an API.

    Args:
        api_name: Name of the API (e.g., "Storage API")

    Returns a list of section names.
    """
    index = get_index(ctx)
    return index.list_sections(api_name)


@mcp.tool()
async def get_request_example(
    ctx: Context,
    api_name: str,
    path: str,
    method: str,
) -> Optional[str]:
    """Generate a curl example for an API endpoint.

    Args:
        api_name: Name of the API (e.g., "Storage API")
        path: URL path (e.g., "/v2/storage/tables")
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)

    Returns a curl command example.
    """
    index = get_index(ctx)
    endpoint = index.get_endpoint(api_name, path, method)

    if not endpoint:
        return None

    return _generate_curl_example(endpoint)


def _endpoint_to_dict(endpoint: Endpoint, brief: bool = False) -> dict:
    """Convert endpoint to dictionary representation."""
    result = {
        "api_name": endpoint.api_name,
        "section": endpoint.section,
        "method": endpoint.method,
        "path": endpoint.path,
        "summary": endpoint.summary,
    }

    if not brief:
        result.update(
            {
                "description": endpoint.description,
                "parameters": [
                    {
                        "name": p.name,
                        "location": p.location,
                        "type": p.type,
                        "required": p.required,
                        "description": p.description,
                        "default": p.default,
                        "example": p.example,
                    }
                    for p in endpoint.parameters
                ],
                "request_example": endpoint.request_example,
                "response_example": endpoint.response_example,
                "auth_header": endpoint.auth_header,
                "base_url": endpoint.base_url,
            }
        )

    return result


def _generate_curl_example(endpoint: Endpoint) -> str:
    """Generate a curl command example for an endpoint."""
    parts = ["curl"]

    # Method
    if endpoint.method != "GET":
        parts.append(f"-X {endpoint.method}")

    # URL
    url = endpoint.base_url or "https://connection.keboola.com"
    url = url.rstrip("/") + endpoint.path
    parts.append(f'"{url}"')

    # Auth header
    if endpoint.auth_header:
        parts.append(f'-H "{endpoint.auth_header}: YOUR_TOKEN"')

    # Content-Type for POST/PUT/PATCH
    if endpoint.method in ["POST", "PUT", "PATCH"]:
        parts.append('-H "Content-Type: application/json"')

        # Add request body if available
        if endpoint.request_example:
            # Compact the JSON for curl
            body = endpoint.request_example.replace("\n", "").replace("  ", "")
            parts.append(f"-d '{body}'")

    return " \\\n  ".join(parts)


def run_server():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    run_server()
