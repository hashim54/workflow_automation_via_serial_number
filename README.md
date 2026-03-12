# Workflow Automation via Serial Number with Python and Microsoft Agent Framework

A FastAPI service that automates data enrichment workflows triggered by a serial number. It integrates with Azure Cosmos DB for persistence, Azure Blob Storage for artifacts, Microsoft Foundry hosted agents for AI reasoning, and MCP servers for external data lookups.

## Prerequisites

- Python 3.12
- Azure subscription

## Getting Started

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1       # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in values as needed. Azure services use `DefaultAzureCredential` — leave credentials empty to rely on managed identity or `az login`.

## Running

```bash
uvicorn app.api.main:app --reload
```

API docs available at `http://localhost:8000/docs`.

The API starts without Azure resources configured — services initialize lazily when first used.

## Testing

```bash
python -m pytest tests -v
```

## Project Structure

```
backend/
├── app/
│   ├── api/          # FastAPI routes and app entry point
│   ├── core/         # Config, container, logger
│   ├── mcp_clients/  # MCP client wrappers (FSG, Phoenix)
│   ├── models/       # Pydantic models
│   ├── services/     # Business logic
│   └── workflows/    # Workflow orchestration and executors
├── mcp_servers/      # MCP server implementations (FSG, Phoenix)
├── tests/
└── requirements.txt
scripts/              # Setup and deployment scripts
```

## Azure Provisioning

The following services must be provisioned and the app's managed identity assigned the roles listed below.

### Azure Cosmos DB

| Setting | Value |
|---|---|
| API | NoSQL |
| Database | `workflow-db` |
| Container | `workflows`, HPK `/user_id` → `/serial_number` (MultiHash v2) |

**RBAC role required:**

| Role | Scope |
|---|---|
| `Cosmos DB Built-in Data Contributor` | Cosmos DB account |

> Use `COSMOS_ENDPOINT` (managed identity) in production. `COSMOS_CONNECTION_STRING` is available for local dev only.

### Azure Blob Storage

| Setting | Value |
|---|---|
| Container | `artifacts` |

**RBAC role required:**

| Role | Scope |
|---|---|
| `Storage Blob Data Contributor` | Storage account or container |

> Use `BLOBSTORAGE_ACCOUNT_URL` (managed identity) in production. `BLOBSTORAGE_CONNECTION_STRING` is available for local dev only.

### Microsoft Foundry

Two hosted agents are required:

| Agent | Purpose |
|---|---|
| Image Processing Agent | Extracts serial numbers from images |
| Reasoning Agent | Analyses enriched data and provides recommendations |

**RBAC role required:**

| Role | Scope |
|---|---|
| `Azure AI Developer` | Microsoft Foundry project |

Set `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_IMAGE_PROCESSING_AGENT_ID`, and `FOUNDRY_REASONING_AGENT_ID` in `.env`.

### Azure App Configuration _(optional)_

Centralises all settings under a key filter (e.g. `workflow-automation:*`). The managed identity needs:

| Role | Scope |
|---|---|
| `App Configuration Data Reader` | App Configuration store |

### Azure Application Insights _(optional)_

Set `APPINSIGHTS_CONNECTION_STRING` to enable distributed tracing via OpenTelemetry. No RBAC required — the connection string contains the ingestion key.

## Configuration

All settings are driven by environment variables. See `.env.example` for the full reference. Azure App Configuration is supported for centralized config management.
