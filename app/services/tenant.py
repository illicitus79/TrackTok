"""Tenant-related helper utilities."""
import re
import secrets
from typing import Dict

from app.models.tenant import Tenant

# Plan / tier definitions that can be managed centrally
PLAN_TIERS: Dict[str, Dict[str, object]] = {
    "basic": {
        "label": "Basic",
        "plan": "basic",
        "max_users": 1,  # single-user tenant for now
        "max_expenses": 100_000,  # total safety cap
        "max_projects": 3,
        "max_accounts": 3,
        "max_project_expenses": 100,  # per project
        "description": "For evaluation and small teams. Limited projects/accounts and per-project expenses.",
    },
    "professional": {
        "label": "Professional",
        "plan": "professional",
        "max_users": 1,  # multi-user can be enabled later
        "max_expenses": 1_000_000,
        "max_projects": 500,
        "max_accounts": 500,
        "max_project_expenses": 1_000_000,
        "description": "Full-feature tier with high limits and all capabilities.",
    },
}


def apply_plan_tier(tenant: Tenant, tier_key: str) -> Tenant:
    """
    Apply a predefined plan tier to a tenant.

    Updates plan name and limit fields based on PLAN_TIERS.
    """
    tier = PLAN_TIERS.get(tier_key)
    if not tier:
        raise ValueError(f"Unknown plan tier: {tier_key}")

    tenant.plan = tier["plan"]
    tenant.max_users = int(tier["max_users"])
    tenant.max_expenses = int(tier["max_expenses"])
    limits = tenant.settings.get("limits", {}) if tenant.settings else {}
    limits.update(
        {
            "max_projects": int(tier["max_projects"]),
            "max_accounts": int(tier["max_accounts"]),
            "max_project_expenses": int(tier["max_project_expenses"]),
        }
    )
    tenant.settings = tenant.settings or {}
    tenant.settings["limits"] = limits
    return tenant


def get_plan_limits(tenant: Tenant) -> Dict[str, int]:
    """
    Return effective limits for a tenant, combining plan defaults with stored overrides.
    """
    plan_key = (tenant.plan or "basic").lower()
    if plan_key == "free":
        plan_key = "basic"
    tier = PLAN_TIERS.get(plan_key, PLAN_TIERS["professional"])
    defaults = {
        "max_projects": int(tier["max_projects"]),
        "max_accounts": int(tier["max_accounts"]),
        "max_project_expenses": int(tier["max_project_expenses"]),
        "max_users": int(tier["max_users"]),
        "max_expenses": int(tier["max_expenses"]),
    }
    overrides = (tenant.settings or {}).get("limits") or {}
    for key, value in overrides.items():
        try:
            defaults[key] = int(value)
        except Exception:
            continue
    return defaults


def _slugify_name(name: str, fallback: str = "tenant") -> str:
    """
    Convert a tenant name into a DNS-friendly slug.

    Keeps lowercase letters, numbers, and hyphens, trims length to 63 chars,
    and ensures we never return an empty string.
    """
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    base = base or fallback
    return base[:63].strip("-") or fallback


def generate_unique_subdomain(name: str) -> str:
    """
    Generate a unique tenant subdomain derived from the provided name.

    If the base slug already exists, append a numeric suffix; after several
    attempts fall back to a short random suffix to guarantee uniqueness.
    """
    base = _slugify_name(name)
    candidate = base
    suffix = 1
    max_length = 63

    while Tenant.query.filter_by(subdomain=candidate).first():
        suffix_str = f"-{suffix}"
        trimmed = base[: max_length - len(suffix_str)].strip("-") or base
        candidate = f"{trimmed}{suffix_str}"
        suffix += 1

        if suffix > 20:
            rand = secrets.token_hex(2)
            candidate = f"{base[: max_length - len(rand) - 1].strip('-')}-{rand}"
            break

    return candidate
