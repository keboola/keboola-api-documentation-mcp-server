# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server that provides AI agents with searchable access to Keboola API documentation. Parses API Blueprint (.apib) and OpenAPI/Swagger specs into a searchable index, exposing tools for searching endpoints, getting details, and generating curl examples.

## Common Commands

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run single test
poetry run pytest tests/test_parsers.py::test_function_name -v

# Format code
poetry run black .

# Lint
poetry run ruff check .
poetry run ruff check . --fix  # auto-fix

# Update API documentation from sources
poetry run keboola-docs update
poetry run keboola-docs update --api storage  # specific API
poetry run keboola-docs update --dry-run      # check without downloading

# List configured sources
poetry run keboola-docs list-sources

# Run MCP server manually
poetry run python -m keboola_docs_mcp.server
```

## Architecture

### Data Flow

1. **Documentation Sources** (`sources.yaml`) - Defines URLs to fetch API docs from (GitHub raw files, Apiary, public endpoints)
2. **Updater** (`updater.py`) - Fetches docs via HTTP, handles GitHub API fallback for private repos using `GITHUB_TOKEN`
3. **Parsers** (`parsers/`) - Convert raw docs to `Endpoint` models:
   - `ApibParser` - Parses API Blueprint format using regex (groups → resources → actions)
   - `OpenApiParser` - Parses OpenAPI/Swagger JSON/YAML specs
4. **Search Index** (`index.py`) - Inverted index with TF-IDF-like scoring for keyword search
5. **MCP Server** (`server.py`) - Exposes tools via FastMCP: `list_apis`, `search_endpoints`, `get_endpoint_details`, `get_api_section`, `list_sections`, `get_request_example`

### Key Models (`models.py`)

- `Endpoint` - API endpoint with path, method, parameters, examples; has `key` property (`api_name:method:path`) and `searchable_text` for indexing
- `Parameter` - Endpoint parameter with location (path/query/header/body)
- `ApiInfo` - API metadata (name, sections, endpoint count)
- `DocumentSource` - Source config from `sources.yaml`

### Configuration

- `sources.yaml` - Documentation sources with `name`, `url`, `output`, `format` (apib/openapi), optional `auth_header` and `base_url`
- Apiary public URLs use format: `https://jsapi.apiary.io/apis/<apiary-name>.apib`

## Code Style

- Line length: 100 characters (black and ruff)
- Python 3.10+ (uses `list[x]` instead of `List[x]`)
- pytest with `asyncio_mode = "auto"`
