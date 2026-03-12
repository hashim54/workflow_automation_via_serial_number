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
| `Storage Blob Data Contributor` | Storage account |

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
| `Azure AI Developer` | AI Services account |

Set `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_IMAGE_PROCESSING_AGENT_ID`, and `FOUNDRY_REASONING_AGENT_ID` in `.env`.

### Azure App Configuration _(optional)_

Centralizes all settings under a key filter (e.g. `workflow-automation:*`). Supports Key Vault references — secrets stored in Key Vault are resolved transparently at startup via `DefaultAzureCredential`.

**RBAC role required:**

| Role | Scope |
|---|---|
| `App Configuration Data Reader` | App Configuration store |

### Azure Key Vault _(optional)_

Used to store secrets referenced from Azure App Configuration. The `azure-appconfiguration-provider` SDK resolves Key Vault reference values automatically at startup — no additional SDK calls are required.

**Requirements:**
- Key Vault must have **RBAC authorization enabled** (`enableRbacAuthorization: true`). Vault access policies are not supported.

**RBAC role required:**

| Role | Scope |
|---|---|
| `Key Vault Secrets User` | Key Vault |

### Azure Application Insights _(optional)_

Set `APPINSIGHTS_CONNECTION_STRING` to enable distributed tracing via OpenTelemetry. No RBAC required — the connection string contains the ingestion key.

## Local Development Setup

Run the interactive setup script to log in to your Entra ID tenant, select a subscription, and assign all required RBAC roles to your local Azure CLI account:

```bash
python scripts/setup_local_dev_rbac.py
```

The script prompts for each resource name and skips services you leave blank. You can also supply everything non-interactively:

```bash
python scripts/setup_local_dev_rbac.py \
  --tenant-id            <tenant-id> \
  --subscription         <subscription-id> \
  --resource-group       <resource-group> \
  --cosmos-account       <cosmos-account-name> \
  --storage-account      <storage-account-name> \
  --ai-services-account  <ai-services-account-name> \
  --app-config-store     <appconfig-store-name> \
  --key-vault            <key-vault-name>
```

After the script completes it prints the endpoint values to copy into `backend/.env`.

> Role propagation can take up to 5 minutes after assignment.

### Next steps after running the script

1. Copy `backend/.env.example` → `backend/.env`
2. Fill in the endpoint values printed by the script
3. Set `FOUNDRY_IMAGE_PROCESSING_AGENT_ID` and `FOUNDRY_REASONING_AGENT_ID`
4. Store secrets in Key Vault and add Key Vault references in App Configuration
5. Run: `cd backend && uvicorn app.api.main:app --reload`

## Configuration

All settings are driven by environment variables. See `.env.example` for the full reference. Azure App Configuration is supported for centralized config management — when `APP_CONFIG_ENDPOINT` is set, all other settings can be stored there, with secrets stored in Key Vault and referenced via Key Vault references.
