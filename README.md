# Keboola API Documentation MCP Server

> Give your AI agents instant access to Keboola API documentation. Search endpoints, get parameter details, and generate curl examples—all through MCP tools.

## Overview

This MCP (Model Context Protocol) server provides AI agents with searchable access to all Keboola API documentation. Instead of manually searching through API docs, your agents can query endpoints, explore sections, and get ready-to-use examples.

**Indexed APIs:**
- Storage API (199 endpoints)
- Management API (129 endpoints)
- Stream Service (41 endpoints)
- Templates Service (23 endpoints)
- Orchestrator API (15 endpoints)
- Metastore Service (14 endpoints)
- Query Service (10 endpoints)
- Generic Extractor API (8 endpoints)
- AppsProxy Service (7 endpoints)

## Features

- **Search endpoints** by keyword, API name, or HTTP method
- **Browse by section** (Tables, Buckets, Jobs, etc.)
- **Get full details** including parameters, request/response examples
- **Generate curl examples** for any endpoint
- **Auto-update** documentation from GitHub sources

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/keboola/keboola-api-documentation-mcp-server
cd keboola-api-documentation-mcp-server

# Install dependencies
poetry install

# Update documentation from GitHub
poetry run keboola-docs update
```

---

## MCP Client Setup

### Claude Desktop Configuration

1. Open Claude Desktop
2. Go to **Claude** (menu) → **Settings** → **Developer** → **Edit Config**
3. Add the following configuration:

```json
{
  "mcpServers": {
    "keboola-docs": {
      "command": "poetry",
      "args": ["--directory", "/path/to/keboola-api-documentation-mcp-server", "run", "python", "-m", "keboola_docs_mcp.server"]
    }
  }
}
```

**Config file locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Claude Code Configuration

Add the MCP server using the Claude Code CLI:

```bash
claude mcp add keboola-docs -- poetry --directory /path/to/keboola-api-documentation-mcp-server run python -m keboola_docs_mcp.server
```

Or add manually to your Claude Code settings:

```json
{
  "mcpServers": {
    "keboola-docs": {
      "command": "poetry",
      "args": ["--directory", "/path/to/keboola-api-documentation-mcp-server", "run", "python", "-m", "keboola_docs_mcp.server"]
    }
  }
}
```

### Cursor Configuration

1. Go to **Settings** → **MCP**
2. Click **"+ Add new global MCP Server"**
3. Configure with these settings:

```json
{
  "mcpServers": {
    "keboola-docs": {
      "command": "poetry",
      "args": ["--directory", "/path/to/keboola-api-documentation-mcp-server", "run", "python", "-m", "keboola_docs_mcp.server"]
    }
  }
}
```

### Windsurf Configuration

Add to your Windsurf MCP settings:

```json
{
  "mcpServers": {
    "keboola-docs": {
      "command": "poetry",
      "args": ["--directory", "/path/to/keboola-api-documentation-mcp-server", "run", "python", "-m", "keboola_docs_mcp.server"]
    }
  }
}
```

### Using uvx (Alternative)

If you prefer using `uvx` instead of Poetry:

```json
{
  "mcpServers": {
    "keboola-docs": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/keboola/keboola-api-documentation-mcp-server", "python", "-m", "keboola_docs_mcp.server"]
    }
  }
}
```

---

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `list_apis()` | List all available Keboola APIs with endpoint counts |
| `search_endpoints(query, api_filter?, method_filter?, limit?)` | Search for endpoints by keyword |
| `get_endpoint_details(api_name, path, method)` | Get full endpoint documentation |
| `get_api_section(api_name, section_name?)` | Get all endpoints in a section |
| `list_sections(api_name)` | List all sections in an API |
| `get_request_example(api_name, path, method)` | Generate curl example |

### Example Queries

Once configured, you can ask your AI agent:

**Searching:**
- "Find endpoints for creating tables in Storage API"
- "Search for token-related endpoints"
- "What POST endpoints exist in the Management API?"

**Exploring:**
- "List all available Keboola APIs"
- "What sections does the Storage API have?"
- "Show me all endpoints in the Tables section"

**Details:**
- "Get details for POST /v2/storage/buckets"
- "Show me a curl example for creating a table"
- "What parameters does the token verification endpoint need?"

---

## CLI Commands

### Update Documentation

Fetch the latest API documentation from GitHub:

```bash
# Update all docs
poetry run keboola-docs update

# Update specific API
poetry run keboola-docs update --api storage

# Dry run (check for updates without downloading)
poetry run keboola-docs update --dry-run
```

### List Sources

```bash
poetry run keboola-docs list-sources
```

### Run Server Manually

```bash
poetry run python -m keboola_docs_mcp.server
```

---

## CI/CD Integration

### GitHub Actions Workflow

The repository includes a workflow that automatically updates documentation daily. It runs at 6:00 UTC and commits any changes.

To trigger manually:
1. Go to **Actions** → **Update API Documentation**
2. Click **Run workflow**

### Custom CI Integration

Add to your workflow:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'

- name: Install Poetry
  uses: snok/install-poetry@v1

- name: Install dependencies
  run: poetry install

- name: Update API documentation
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: poetry run keboola-docs update

- name: Commit changes
  run: |
    git add docs/
    git diff --staged --quiet || git commit -m "chore: update API docs"
    git push
```

---

## Configuration

### sources.yaml

Documentation sources are configured in `sources.yaml`. Each source specifies:
- `name`: API display name
- `url`: GitHub raw URL to fetch from
- `output`: Local file path
- `format`: `apib` (API Blueprint) or `openapi`
- `description`: Brief description
- `auth_header`: Authentication header name (optional)
- `base_url`: API base URL (optional)

Example:

```yaml
sources:
  - name: Storage API
    url: https://raw.githubusercontent.com/keboola/storage-api-php-client/master/apiary.apib
    output: docs/apiary/storage-api.apib
    format: apib
    description: Core data storage API
    auth_header: X-StorageApi-Token
    base_url: https://connection.keboola.com
```

### Private Repositories

The updater automatically uses `GITHUB_TOKEN` or `GH_TOKEN` environment variables to access private repositories. In CI, this is provided by GitHub Actions automatically.

---

## Development

### Running Tests

```bash
poetry run pytest
```

### Project Structure

```
keboola-api-documentation-mcp-server/
├── docs/
│   ├── apiary/          # API Blueprint documentation
│   └── openapi/         # OpenAPI/Swagger specs
├── src/keboola_docs_mcp/
│   ├── server.py        # MCP server with tools
│   ├── cli.py           # CLI commands
│   ├── updater.py       # Documentation fetcher
│   ├── index.py         # Search index
│   ├── models.py        # Data models
│   └── parsers/         # API Blueprint & OpenAPI parsers
├── tests/
├── sources.yaml         # Documentation sources config
└── pyproject.toml
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **No endpoints found** | Run `poetry run keboola-docs update` to fetch docs |
| **HTTP 404 errors** | Check `GITHUB_TOKEN` is set for private repos |
| **Server won't start** | Ensure Poetry dependencies are installed |
| **Search returns nothing** | Try broader search terms or check API name |

---

## Resources

- [Keboola Developer Documentation](https://developers.keboola.com/)
- [Storage API Reference](https://keboola.docs.apiary.io/)
- [Management API Reference](https://keboolamanagementapi.docs.apiary.io/)
- [MCP Protocol](https://modelcontextprotocol.io/)

## License

MIT
