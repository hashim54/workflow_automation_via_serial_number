#!/usr/bin/env python3
"""
Local developer RBAC setup

Logs in to Azure, selects a subscription, and assigns all RBAC roles required
to run the Workflow Automation service locally with DefaultAzureCredential.

Roles assigned to the signed-in user:

  Service               Role                              Assignment scope
  ──────────────────────────────────────────────────────────────────────────
  Cosmos DB (NoSQL)     Cosmos DB Built-in Data Contributor  Cosmos account
  Blob Storage          Storage Blob Data Contributor         Storage account
  Microsoft Foundry     Azure AI Developer                    AI Services account
  App Configuration     App Configuration Data Reader         AppConfig store
  Key Vault             Key Vault Secrets User                Key Vault

Usage:
    python scripts/setup_local_dev_rbac.py

    # Non-interactive (all values supplied up-front):
    python scripts/setup_local_dev_rbac.py \\
        --tenant-id   <tenant-id> \\
        --subscription <subscription-id-or-name> \\
        --resource-group <rg> \\
        --cosmos-account <cosmos-account-name> \\
        --storage-account <storage-account-name> \\
        --ai-services-account <ai-services-account-name> \\
        --app-config-store <appconfig-store-name> \\
        --key-vault <key-vault-name>

Any resource flag left out causes that service to be skipped.
"""

import argparse
import json
import subprocess
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Terminal colour helpers
# ---------------------------------------------------------------------------

RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
BOLD = "\033[1m"


def _c(colour: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"{colour}{text}{RESET}"
    return text


def print_header(msg: str) -> None:
    width = max(len(msg) + 4, 66)
    print(_c(CYAN, "\n" + "═" * width))
    print(_c(CYAN + BOLD, f"  {msg}"))
    print(_c(CYAN, "═" * width))


def print_section(msg: str) -> None:
    print(_c(CYAN, f"\n─── {msg} ───"))


def print_step(msg: str) -> None:
    print(_c(CYAN, f"  › {msg}"))


def print_success(msg: str) -> None:
    print(_c(GREEN, f"  ✓ {msg}"))


def print_warning(msg: str) -> None:
    print(_c(YELLOW, f"  ⚠ {msg}"))


def print_error(msg: str) -> None:
    print(_c(RED, f"  ✗ {msg}"), file=sys.stderr)


def print_detail(msg: str) -> None:
    print(f"      {msg}")


def print_skip(msg: str) -> None:
    print(_c(YELLOW, f"  ⊘ Skipped: {msg}"))


# ---------------------------------------------------------------------------
# Azure CLI helpers
# ---------------------------------------------------------------------------


def _run(args: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=capture,
        text=True,
        shell=sys.platform == "win32",
    )


def _run_json(args: list[str]) -> tuple[bool, object]:
    result = _run(args)
    if result.returncode != 0:
        return False, result.stderr.strip()
    try:
        return True, json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, result.stdout.strip()


def _run_str(args: list[str]) -> tuple[bool, str]:
    result = _run(args)
    return result.returncode == 0, result.stdout.strip()


# ---------------------------------------------------------------------------
# Step 1 – Prerequisites
# ---------------------------------------------------------------------------


def check_prereqs() -> None:
    print_section("Prerequisites")
    ok, _ = _run_str(["az", "--version"])
    if not ok:
        print_error("Azure CLI is not installed. Install from https://aka.ms/azure-cli")
        sys.exit(1)
    print_success("Azure CLI found")


# ---------------------------------------------------------------------------
# Step 2 – Login / tenant
# ---------------------------------------------------------------------------


def ensure_login(tenant_id: Optional[str]) -> dict:
    """Return the active account dict, prompting for login when needed."""
    print_section("Authentication")

    ok, account = _run_json(["az", "account", "show"])
    if ok and isinstance(account, dict):
        user = account.get("user", {}).get("name", "<unknown>")
        print_success(f"Already signed in as: {_c(WHITE, user)}")
        return account

    # Not logged in — trigger interactive login
    print_step("Not signed in — launching az login...")
    login_cmd = ["az", "login"]
    if tenant_id:
        login_cmd += ["--tenant", tenant_id]

    result = _run(login_cmd, capture=False)
    if result.returncode != 0:
        print_error("Login failed.")
        sys.exit(1)

    ok, account = _run_json(["az", "account", "show"])
    if not ok or not isinstance(account, dict):
        print_error("Could not retrieve account after login.")
        sys.exit(1)

    user = account.get("user", {}).get("name", "<unknown>")
    print_success(f"Signed in as: {_c(WHITE, user)}")
    return account


# ---------------------------------------------------------------------------
# Step 3 – Subscription selection
# ---------------------------------------------------------------------------


def select_subscription(subscription_arg: Optional[str]) -> str:
    """Return the subscription ID to use, prompting interactively if needed."""
    print_section("Subscription")

    ok, subs = _run_json(["az", "account", "list", "--query", "[].{id:id, name:name, state:state}", "-o", "json"])
    if not ok or not isinstance(subs, list):
        print_error("Could not list subscriptions.")
        sys.exit(1)

    active_subs = [s for s in subs if s.get("state") == "Enabled"]
    if not active_subs:
        print_error("No enabled subscriptions found.")
        sys.exit(1)

    # If a specific subscription was requested, find it
    if subscription_arg:
        for s in active_subs:
            if s["id"] == subscription_arg or s["name"] == subscription_arg:
                _set_subscription(s["id"])
                print_success(f"Using subscription: {s['name']} ({s['id']})")
                return s["id"]
        print_error(f"Subscription '{subscription_arg}' not found or not enabled.")
        sys.exit(1)

    # Single subscription — use it automatically
    if len(active_subs) == 1:
        sub = active_subs[0]
        _set_subscription(sub["id"])
        print_success(f"Using subscription: {sub['name']} ({sub['id']})")
        return sub["id"]

    # Interactive selection
    print()
    print(_c(WHITE, "  Available subscriptions:"))
    for i, s in enumerate(active_subs, 1):
        print(f"    [{i}] {s['name']}")
        print_detail(s["id"])

    while True:
        try:
            choice = input(_c(CYAN, "\n  Select subscription number: ")).strip()
            idx = int(choice) - 1
            if 0 <= idx < len(active_subs):
                sub = active_subs[idx]
                _set_subscription(sub["id"])
                print_success(f"Using subscription: {sub['name']} ({sub['id']})")
                return sub["id"]
        except (ValueError, KeyboardInterrupt):
            pass
        print_warning("Invalid selection, try again.")


def _set_subscription(sub_id: str) -> None:
    ok, _ = _run_str(["az", "account", "set", "--subscription", sub_id])
    if not ok:
        print_error(f"Failed to set subscription {sub_id}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Step 4 – Resolve current user object ID
# ---------------------------------------------------------------------------


def get_current_user_id() -> str:
    print_section("Signed-in user identity")
    ok, uid = _run_str(["az", "ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"])
    if not ok or not uid:
        print_error(
            "Could not retrieve signed-in user object ID. Are you logged in as a user (not a service principal)?"
        )
        sys.exit(1)
    print_success(f"User object ID: {_c(WHITE, uid)}")
    return uid


# ---------------------------------------------------------------------------
# RBAC assignment helpers
# ---------------------------------------------------------------------------


def _resource_exists(check_cmd: list[str], resource_label: str) -> bool:
    ok, _ = _run_json(check_cmd)
    if not ok:
        print_warning(f"{resource_label} not found or not accessible — skipping.")
        return False
    return True


def _assign_arm_role(role: str, scope: str, principal_id: str, resource_label: str) -> None:
    """Assign a standard Azure ARM RBAC role, idempotent."""
    # Check if already assigned
    ok, existing = _run_json(
        [
            "az",
            "role",
            "assignment",
            "list",
            "--assignee",
            principal_id,
            "--role",
            role,
            "--scope",
            scope,
            "--query",
            "[].id",
            "-o",
            "json",
        ]
    )
    if ok and isinstance(existing, list) and existing:
        print_warning(f"'{role}' already assigned on {resource_label}")
        return

    ok, result = _run_json(
        [
            "az",
            "role",
            "assignment",
            "create",
            "--assignee",
            principal_id,
            "--role",
            role,
            "--scope",
            scope,
        ]
    )
    if ok:
        print_success(f"Assigned '{role}' on {resource_label}")
    else:
        print_error(f"Failed to assign '{role}' on {resource_label}: {result}")


def _assign_cosmos_data_role(
    resource_group: str,
    account_name: str,
    principal_id: str,
    subscription_id: str,
) -> None:
    """Assign the Cosmos DB Built-in Data Contributor role (data-plane)."""
    # Built-in role GUID — fixed across all accounts
    role_def_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.DocumentDB/databaseAccounts/{account_name}"
        f"/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
    )

    # Check existing
    ok, existing = _run_json(
        [
            "az",
            "cosmosdb",
            "sql",
            "role",
            "assignment",
            "list",
            "--account-name",
            account_name,
            "--resource-group",
            resource_group,
            "--query",
            f"[?principalId=='{principal_id}' && contains(roleDefinitionId, '00000000-0000-0000-0000-000000000002')]",
        ]
    )
    if ok and isinstance(existing, list) and existing:
        print_warning("'Cosmos DB Built-in Data Contributor' already assigned")
        return

    ok, result = _run_json(
        [
            "az",
            "cosmosdb",
            "sql",
            "role",
            "assignment",
            "create",
            "--account-name",
            account_name,
            "--resource-group",
            resource_group,
            "--scope",
            "/",
            "--principal-id",
            principal_id,
            "--role-definition-id",
            role_def_id,
        ]
    )
    if ok:
        print_success("Assigned 'Cosmos DB Built-in Data Contributor' (data-plane)")
    else:
        print_error(f"Failed to assign Cosmos DB data role: {result}")
        print_detail("Tip: your account may need 'Owner' or 'User Access Administrator' on the Cosmos account.")


# ---------------------------------------------------------------------------
# Step 5 – Per-service role assignments
# ---------------------------------------------------------------------------


def setup_cosmos(resource_group: str, account_name: str, principal_id: str, subscription_id: str) -> None:
    print_section(f"Cosmos DB  [{account_name}]")
    if not _resource_exists(
        ["az", "cosmosdb", "show", "--name", account_name, "--resource-group", resource_group],
        f"Cosmos DB account '{account_name}'",
    ):
        return

    ok, account = _run_json(["az", "cosmosdb", "show", "--name", account_name, "--resource-group", resource_group])
    endpoint = account.get("documentEndpoint", "") if isinstance(account, dict) else ""

    _assign_cosmos_data_role(resource_group, account_name, principal_id, subscription_id)

    if endpoint:
        print()
        print(_c(YELLOW, "  Add to .env:"))
        print(_c(WHITE, f"  COSMOS_ENDPOINT={endpoint}"))


def setup_storage(resource_group: str, account_name: str, principal_id: str, subscription_id: str) -> None:
    print_section(f"Blob Storage  [{account_name}]")
    if not _resource_exists(
        ["az", "storage", "account", "show", "--name", account_name, "--resource-group", resource_group],
        f"Storage account '{account_name}'",
    ):
        return

    ok, sa = _run_json(["az", "storage", "account", "show", "--name", account_name, "--resource-group", resource_group])
    sa_id = sa.get("id", "") if isinstance(sa, dict) else ""
    blob_endpoint = sa.get("primaryEndpoints", {}).get("blob", "") if isinstance(sa, dict) else ""

    _assign_arm_role("Storage Blob Data Contributor", sa_id, principal_id, account_name)

    if blob_endpoint:
        print()
        print(_c(YELLOW, "  Add to .env:"))
        print(_c(WHITE, f"  BLOBSTORAGE_ACCOUNT_URL={blob_endpoint}"))


def setup_ai_services(resource_group: str, account_name: str, principal_id: str, subscription_id: str) -> None:
    print_section(f"Microsoft Foundry / AI Services  [{account_name}]")
    if not _resource_exists(
        ["az", "cognitiveservices", "account", "show", "--name", account_name, "--resource-group", resource_group],
        f"AI Services account '{account_name}'",
    ):
        return

    ok, ai = _run_json(
        ["az", "cognitiveservices", "account", "show", "--name", account_name, "--resource-group", resource_group]
    )
    ai_id = ai.get("id", "") if isinstance(ai, dict) else ""

    _assign_arm_role("Azure AI Developer", ai_id, principal_id, account_name)

    endpoint = ai.get("properties", {}).get("endpoint", "") if isinstance(ai, dict) else ""
    if endpoint:
        print()
        print(_c(YELLOW, "  Add to .env:"))
        print(_c(WHITE, f"  FOUNDRY_PROJECT_ENDPOINT={endpoint}"))


def setup_app_config(resource_group: str, store_name: str, principal_id: str, subscription_id: str) -> None:
    print_section(f"App Configuration  [{store_name}]")
    if not _resource_exists(
        ["az", "appconfig", "show", "--name", store_name, "--resource-group", resource_group],
        f"App Configuration store '{store_name}'",
    ):
        return

    ok, ac = _run_json(["az", "appconfig", "show", "--name", store_name, "--resource-group", resource_group])
    ac_id = ac.get("id", "") if isinstance(ac, dict) else ""
    endpoint = ac.get("endpoint", "") if isinstance(ac, dict) else ""

    _assign_arm_role("App Configuration Data Reader", ac_id, principal_id, store_name)

    if endpoint:
        print()
        print(_c(YELLOW, "  Add to .env:"))
        print(_c(WHITE, f"  APP_CONFIG_ENDPOINT={endpoint}"))


def setup_key_vault(resource_group: str, vault_name: str, principal_id: str, subscription_id: str) -> None:
    """Assign 'Key Vault Secrets User' so the runtime identity can resolve Key Vault references
    stored in Azure App Configuration. Uses RBAC authorization — no access policies required.
    """
    print_section(f"Key Vault  [{vault_name}]")
    if not _resource_exists(
        ["az", "keyvault", "show", "--name", vault_name, "--resource-group", resource_group],
        f"Key Vault '{vault_name}'",
    ):
        return

    ok, kv = _run_json(["az", "keyvault", "show", "--name", vault_name, "--resource-group", resource_group])
    if not ok or not isinstance(kv, dict):
        print_error(f"Could not retrieve Key Vault '{vault_name}'.")
        return

    kv_id = kv.get("id", "")
    vault_uri = kv.get("properties", {}).get("vaultUri", "")

    # Verify the vault uses RBAC authorization (not vault access policies).
    # RBAC auth is required for role-assignment-based access.
    rbac_enabled = kv.get("properties", {}).get("enableRbacAuthorization", False)
    if not rbac_enabled:
        print_warning(f"Key Vault '{vault_name}' does not have RBAC authorization enabled. " "Enable it with:")
        print_detail(
            f"az keyvault update --name {vault_name} "
            f"--resource-group {resource_group} --enable-rbac-authorization true"
        )
        return

    _assign_arm_role("Key Vault Secrets User", kv_id, principal_id, vault_name)

    if vault_uri:
        print()
        print(_c(YELLOW, "  Store secrets here and reference them from App Configuration:"))
        print(_c(WHITE, f"    Vault URI: {vault_uri}"))
        print(_c(CYAN, "  In the App Configuration store, add a 'Key Vault reference' value"))
        print(_c(CYAN, "  pointing to each secret. The SDK resolves them automatically at startup."))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(args: argparse.Namespace) -> None:
    print_header("Setup complete")
    print()
    print(_c(CYAN, "  Role propagation can take up to 5 minutes."))
    print()
    print(_c(WHITE, "  Next steps:"))
    print("    1. Copy backend/.env.example  →  backend/.env")
    print("    2. Fill in the endpoint values printed above")
    print("    3. Set FOUNDRY_IMAGE_PROCESSING_AGENT_ID and FOUNDRY_REASONING_AGENT_ID")
    print("    4. Store secrets in Key Vault and add Key Vault references in App Configuration")
    print("    5. Run:  cd backend && uvicorn app.api.main:app --reload")
    print()
    print(_c(CYAN, "  Use 'az login' again at any time to refresh credentials."))
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="setup_local_dev_rbac.py",
        description=(
            "Assign Azure RBAC roles for local development to the currently signed-in user. "
            "Omit a resource flag to skip that service."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--tenant-id", "-t", metavar="TENANT_ID", help="Entra ID tenant ID (used if login is needed).")
    parser.add_argument(
        "--subscription", "-s", metavar="SUBSCRIPTION", help="Subscription name or ID (interactive if omitted)."
    )
    parser.add_argument(
        "--resource-group", "-g", metavar="RESOURCE_GROUP", help="Resource group that contains all services."
    )
    parser.add_argument("--cosmos-account", metavar="ACCOUNT_NAME", help="Cosmos DB account name.")
    parser.add_argument("--storage-account", metavar="ACCOUNT_NAME", help="Storage account name.")
    parser.add_argument(
        "--ai-services-account",
        metavar="ACCOUNT_NAME",
        help="Azure AI Services / Cognitive Services account name (Microsoft Foundry).",
    )
    parser.add_argument(
        "--app-config-store",
        metavar="STORE_NAME",
        help="App Configuration store name (optional — skipped if not supplied).",
    )
    parser.add_argument(
        "--key-vault",
        metavar="VAULT_NAME",
        help="Key Vault name (optional — skipped if not supplied). "
        "Assigns 'Key Vault Secrets User' role; vault must have RBAC authorization enabled.",
    )
    return parser


def _prompt_if_missing(current: Optional[str], prompt: str) -> Optional[str]:
    """Return current if set, otherwise prompt the user (empty input = skip)."""
    if current:
        return current
    value = input(_c(CYAN, f"  {prompt} (leave blank to skip): ")).strip()
    return value or None


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    print_header("Workflow Automation — Local Dev RBAC Setup")

    check_prereqs()
    ensure_login(args.tenant_id)
    subscription_id = select_subscription(args.subscription)
    principal_id = get_current_user_id()

    # Resolve resource group — required if any resource is being configured
    print_section("Resources to configure")
    print(_c(WHITE, "  Leave blank to skip a service.\n"))

    resource_group = _prompt_if_missing(args.resource_group, "Resource group name")
    if not resource_group:
        print_warning("No resource group provided — nothing to configure.")
        sys.exit(0)

    cosmos_account = _prompt_if_missing(args.cosmos_account, "Cosmos DB account name")
    storage_account = _prompt_if_missing(args.storage_account, "Storage account name")
    ai_services_account = _prompt_if_missing(args.ai_services_account, "AI Services account name (Foundry)")
    app_config_store = _prompt_if_missing(args.app_config_store, "App Configuration store name")
    key_vault = _prompt_if_missing(args.key_vault, "Key Vault name")

    # Assign roles
    if cosmos_account:
        setup_cosmos(resource_group, cosmos_account, principal_id, subscription_id)
    else:
        print_skip("Cosmos DB")

    if storage_account:
        setup_storage(resource_group, storage_account, principal_id, subscription_id)
    else:
        print_skip("Blob Storage")

    if ai_services_account:
        setup_ai_services(resource_group, ai_services_account, principal_id, subscription_id)
    else:
        print_skip("Microsoft Foundry / AI Services")

    if app_config_store:
        setup_app_config(resource_group, app_config_store, principal_id, subscription_id)
    else:
        print_skip("App Configuration")

    if key_vault:
        setup_key_vault(resource_group, key_vault, principal_id, subscription_id)
    else:
        print_skip("Key Vault")

    print_summary(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(_c(YELLOW, "\n\n  Interrupted."))
        sys.exit(1)
