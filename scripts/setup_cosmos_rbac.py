#!/usr/bin/env python3
"""
Setup Cosmos DB RBAC

Sets up a Cosmos DB data-plane RBAC role definition and assignment.

Creates a custom role with full data-plane permissions and assigns it to a
specified principal (user, managed identity, or service principal).

Usage:
    python setup_cosmos_rbac.py --help
    python setup_cosmos_rbac.py \\
        --resource-group myRG \\
        --account-name myCosmosAccount \\
        --principal-id 12345678-1234-1234-1234-123456789abc

    # Get your user object ID:
    az ad signed-in-user show --query id -o tsv

    # Get a managed identity principal ID:
    az identity show --name <identity-name> --resource-group <rg> --query principalId -o tsv
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Terminal colour helpers (ANSI; work on all modern terminals including Windows
# with Virtual Terminal Processing enabled, which is the default since Win 10)
# ---------------------------------------------------------------------------

RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"


def _c(colour: str, text: str) -> str:
    """Wrap *text* with an ANSI colour code if stdout is a TTY."""
    if sys.stdout.isatty():
        return f"{colour}{text}{RESET}"
    return text


def print_header(msg: str) -> None:
    print(_c(CYAN, f"\n{'=' * 66}"))
    print(_c(CYAN, msg))
    print(_c(CYAN, "=" * 66))


def print_step(msg: str) -> None:
    print(_c(CYAN, f"\n>>> {msg}"))


def print_success(msg: str) -> None:
    print(_c(GREEN, f"  \u2713 {msg}"))


def print_warning(msg: str) -> None:
    print(_c(YELLOW, f"  \u26a0 {msg}"))


def print_error(msg: str) -> None:
    print(_c(RED, f"  \u2717 {msg}"), file=sys.stderr)


def print_detail(msg: str) -> None:
    print(f"    {msg}")


# ---------------------------------------------------------------------------
# Azure CLI helpers
# ---------------------------------------------------------------------------


def _run(args: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run an Azure CLI command and return the CompletedProcess."""
    # On Windows, `az` is a .cmd wrapper; shell=True is required to locate it.
    return subprocess.run(
        args,
        capture_output=capture,
        text=True,
        shell=sys.platform == "win32",
    )


def _run_json(args: list[str]) -> tuple[bool, object]:
    """
    Run an Azure CLI command and return (success, parsed_json_output).
    Returns (False, None) on non-zero exit or JSON parse failure.
    """
    result = _run(args)
    if result.returncode != 0:
        return False, result.stderr.strip()
    try:
        return True, json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, result.stdout.strip()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_prerequisites() -> None:
    print_step("Validating prerequisites...")

    result = _run(["az", "--version"])
    if result.returncode != 0:
        print_error("Azure CLI is not installed. Install it from https://aka.ms/azure-cli")
        sys.exit(1)
    print_success("Azure CLI is installed")


def validate_auth() -> dict:
    print_step("Validating Azure authentication...")

    ok, account = _run_json(["az", "account", "show"])
    if not ok or not isinstance(account, dict):
        print_error("Not authenticated with Azure. Run 'az login' first.")
        sys.exit(1)

    user_name = account.get("user", {}).get("name", "<unknown>")
    sub_name = account.get("name", "<unknown>")
    sub_id = account.get("id", "<unknown>")

    print_success(f"Authenticated as: {user_name}")
    print_detail(f"Subscription: {sub_name} ({sub_id})")
    return account


def validate_cosmos_account(resource_group: str, account_name: str) -> dict:
    print_step("Validating Cosmos DB account...")

    ok, cosmos = _run_json(
        [
            "az",
            "cosmosdb",
            "show",
            "--name",
            account_name,
            "--resource-group",
            resource_group,
        ]
    )
    if not ok or not isinstance(cosmos, dict):
        print_error(f"Cosmos DB account '{account_name}' not found in resource group '{resource_group}'")
        sys.exit(1)

    endpoint = cosmos.get("documentEndpoint", "<unknown>")
    print_success(f"Found Cosmos DB account: {account_name}")
    print_detail(f"Endpoint: {endpoint}")
    return cosmos


# ---------------------------------------------------------------------------
# Role definition
# ---------------------------------------------------------------------------


def ensure_role_definition(resource_group: str, account_name: str, role_name: str) -> str:
    """Return the role definition ID, creating the role if it does not exist."""
    print_step("Checking for existing role definition...")

    ok, existing = _run_json(
        [
            "az",
            "cosmosdb",
            "sql",
            "role",
            "definition",
            "list",
            "--account-name",
            account_name,
            "--resource-group",
            resource_group,
            "--query",
            f"[?roleName=='{role_name}']",
        ]
    )

    if ok and isinstance(existing, list) and existing:
        role_id = existing[0]["name"]
        print_warning(f"Role '{role_name}' already exists")
        print_detail(f"Using existing role ID: {role_id}")
        return role_id

    # Build role definition
    print_step("Creating custom role definition...")
    role_body = {
        "RoleName": role_name,
        "Type": "CustomRole",
        "AssignableScopes": ["/"],
        "Permissions": [
            {
                "DataActions": [
                    "Microsoft.DocumentDB/databaseAccounts/readMetadata",
                    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/create",
                    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/read",
                    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/delete",
                    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/upsert",
                    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/replace",
                    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/executeQuery",
                    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/write",
                    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/write",
                ]
            }
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(role_body, tmp, indent=2)
        tmp_path = tmp.name

    try:
        ok, result = _run_json(
            [
                "az",
                "cosmosdb",
                "sql",
                "role",
                "definition",
                "create",
                "--account-name",
                account_name,
                "--resource-group",
                resource_group,
                "--body",
                f"@{tmp_path}",
            ]
        )
    finally:
        os.unlink(tmp_path)

    if not ok or not isinstance(result, dict):
        print_error(f"Failed to create role definition: {result}")
        sys.exit(1)

    role_id = result["name"]
    print_success(f"Role definition created: {role_name}")
    print_detail(f"Role ID: {role_id}")
    return role_id


# ---------------------------------------------------------------------------
# Role assignment
# ---------------------------------------------------------------------------


def ensure_role_assignment(
    resource_group: str,
    account_name: str,
    principal_id: str,
    role_definition_id: str,
) -> None:
    print_step("Checking for existing role assignment...")

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
            f"[?principalId=='{principal_id}' && contains(roleDefinitionId, '{role_definition_id}')]",
        ]
    )

    if ok and isinstance(existing, list) and existing:
        print_warning(f"Role already assigned to principal {principal_id}")
        print_detail(f"Assignment ID: {existing[0]['name']}")
        return

    print_step("Assigning role to principal...")
    ok, assignment = _run_json(
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
            role_definition_id,
        ]
    )

    if not ok or not isinstance(assignment, dict):
        print_error(f"Failed to create role assignment: {assignment}")
        sys.exit(1)

    print_success("Role assigned successfully")
    print_detail(f"Assignment ID: {assignment['name']}")
    print_detail(f"Principal ID:  {assignment['principalId']}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="setup_cosmos_rbac.py",
        description=("Creates a custom Cosmos DB data-plane RBAC role and assigns it " "to the specified principal."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python setup_cosmos_rbac.py \\\n"
            "      --resource-group myRG \\\n"
            "      --account-name myCosmosAccount \\\n"
            "      --principal-id 12345678-1234-1234-1234-123456789abc\n\n"
            "  # Current user ID\n"
            "  az ad signed-in-user show --query id -o tsv\n\n"
            "  # Managed identity principal ID\n"
            "  az identity show --name <name> --resource-group <rg> --query principalId -o tsv\n"
        ),
    )
    parser.add_argument(
        "--resource-group",
        "-g",
        required=True,
        metavar="RESOURCE_GROUP",
        help="Resource group containing the Cosmos DB account.",
    )
    parser.add_argument(
        "--account-name",
        "-a",
        required=True,
        metavar="ACCOUNT_NAME",
        help="Name of the Cosmos DB account.",
    )
    parser.add_argument(
        "--principal-id",
        "-p",
        required=True,
        metavar="PRINCIPAL_ID",
        help="Object ID of the principal (user / managed identity / service principal).",
    )
    parser.add_argument(
        "--role-name",
        "-r",
        default="CosmosDB-DataPlane-FullAccess",
        metavar="ROLE_NAME",
        help="Name for the custom role (default: CosmosDB-DataPlane-FullAccess).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    print_header("Cosmos DB RBAC Setup")

    try:
        validate_prerequisites()
        validate_auth()
        cosmos_account = validate_cosmos_account(args.resource_group, args.account_name)

        role_id = ensure_role_definition(args.resource_group, args.account_name, args.role_name)
        ensure_role_assignment(args.resource_group, args.account_name, args.principal_id, role_id)

        # Summary
        endpoint = cosmos_account.get("documentEndpoint", "<unknown>")
        print_header(_c(GREEN, "\u2713 Setup Complete!"))
        print()
        print(_c(WHITE, f"  Role Name:       {args.role_name}"))
        print(_c(WHITE, f"  Principal ID:    {args.principal_id}"))
        print(_c(WHITE, f"  Cosmos Account:  {args.account_name}"))
        print(_c(WHITE, f"  Resource Group:  {args.resource_group}"))
        print()
        print_warning("Role propagation can take 5-10 minutes. Please wait before testing.")
        print()
        print(_c(CYAN, "  Add this to your .env file:"))
        print(_c(YELLOW, f"  COSMOS_ENDPOINT={endpoint}"))
        print()

    except KeyboardInterrupt:
        print()
        print_error("Interrupted by user.")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001
        print_header(_c(RED, "\u2717 Setup Failed!"))
        print()
        print_error(f"Error: {exc}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
