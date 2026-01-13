"""MCP server for Keboola API documentation."""

from contextlib import asynccontextmanager
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP

from .index import SearchIndex, build_index
from .models import Endpoint

# Mapping of auth headers to recommended environment variable names
AUTH_HEADER_TO_ENV_VAR = {
    "X-StorageApi-Token": "KBC_STORAGE_API_TOKEN",
    "X-KBC-ManageApiToken": "KBC_MANAGE_API_TOKEN",
}


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
async def get_connection_info() -> dict:
    """Get information about how to connect to Keboola APIs.

    Returns details about:
    - Required environment variables for authentication tokens
    - Host/stack configuration (Keboola has multiple environments)
    - How to construct API requests

    IMPORTANT: Always call this first to understand how to configure API access.
    """
    return {
        "host_configuration": {
            "note": "Keboola has multiple stacks. The host URL depends on the user's environment.",
            "env_var": "KBC_STORAGE_API_URL",
            "example_hosts": [
                "https://connection.keboola.com (US)",
                "https://connection.eu-central-1.keboola.com (EU)",
                "https://connection.us-east4.gcp.keboola.com (GCP US)",
                "https://connection.north-europe.azure.keboola.com (Azure EU)",
            ],
            "instruction": "Ask the user for their Keboola stack URL or check KBC_STORAGE_API_URL env var.",
        },
        "authentication": {
            "storage_api": {
                "header": "X-StorageApi-Token",
                "env_var": "KBC_STORAGE_API_TOKEN",
                "used_by": ["Storage API", "most component APIs"],
            },
            "manage_api": {
                "header": "X-KBC-ManageApiToken",
                "env_var": "KBC_MANAGE_API_TOKEN",
                "used_by": ["Management API"],
            },
        },
        "curl_example": (
            'curl "$KBC_STORAGE_API_URL/v2/storage/buckets" \\\n'
            '  -H "X-StorageApi-Token: $KBC_STORAGE_API_TOKEN"'
        ),
    }


@mcp.tool()
async def list_apis(ctx: Context) -> list[dict]:
    """List all available Keboola APIs.

    Returns a list of APIs with their names, descriptions, and endpoint counts.

    Note: Base URLs shown are examples. Actual host depends on user's Keboola stack.
    Use get_connection_info() to understand host and token configuration.
    """
    index = get_index(ctx)
    apis = index.list_apis()
    return [
        {
            "name": api.name,
            "description": api.description,
            "base_url": api.base_url,
            "base_url_note": "Example only - actual host depends on user's Keboola stack",
            "auth_header": api.auth_header,
            "token_env_var": AUTH_HEADER_TO_ENV_VAR.get(api.auth_header),
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
    token_env_var = None
    if endpoint.auth_header:
        token_env_var = AUTH_HEADER_TO_ENV_VAR.get(endpoint.auth_header)

    result: dict = {
        "api_name": endpoint.api_name,
        "section": endpoint.section,
        "method": endpoint.method,
        "path": endpoint.path,
        "summary": endpoint.summary,
    }

    if not brief:
        result["description"] = endpoint.description
        result["parameters"] = [
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
        ]
        result["request_example"] = endpoint.request_example
        result["response_example"] = endpoint.response_example
        result["auth_header"] = endpoint.auth_header
        result["token_env_var"] = token_env_var
        result["base_url"] = endpoint.base_url
        result["base_url_note"] = "Example only - use $KBC_STORAGE_API_URL env var"

    return result


def _generate_curl_example(endpoint: Endpoint) -> str:
    """Generate a curl command example for an endpoint using environment variables."""
    parts = ["curl"]

    # Method
    if endpoint.method != "GET":
        parts.append(f"-X {endpoint.method}")

    # URL - use env var for host
    parts.append(f'"$KBC_STORAGE_API_URL{endpoint.path}"')

    # Auth header - use env var for token
    if endpoint.auth_header:
        token_env_var = AUTH_HEADER_TO_ENV_VAR.get(endpoint.auth_header, "KBC_TOKEN")
        parts.append(f'-H "{endpoint.auth_header}: ${token_env_var}"')

    # Content-Type for POST/PUT/PATCH
    if endpoint.method in ["POST", "PUT", "PATCH"]:
        parts.append('-H "Content-Type: application/json"')

        # Add request body if available
        if endpoint.request_example:
            # Compact the JSON for curl
            body = endpoint.request_example.replace("\n", "").replace("  ", "")
            parts.append(f"-d '{body}'")

    example = " \\\n  ".join(parts)

    # Add note about environment variables
    note = (
        "\n\n# Required environment variables:\n"
        "#   KBC_STORAGE_API_URL - Your Keboola stack URL (e.g., https://connection.keboola.com)\n"
    )
    if endpoint.auth_header:
        token_env_var = AUTH_HEADER_TO_ENV_VAR.get(endpoint.auth_header, "KBC_TOKEN")
        note += f"#   {token_env_var} - Your API token\n"

    return example + note


def run_server():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    run_server()
