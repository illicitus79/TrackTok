"""Tenant-related helper utilities."""
import re
import secrets

from app.models.tenant import Tenant


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
