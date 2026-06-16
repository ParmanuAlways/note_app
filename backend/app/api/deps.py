"""Shared request dependencies."""

from __future__ import annotations

# v1 is single-user (requirements §2.5). Until Keycloak token validation lands
# (FR-40), every request is attributed to this fixed owner. The schema already
# carries owner_id/unit_id, so swapping this for a real identity is a one-line
# change with no migration.
DEFAULT_OWNER_ID = "default-user"


def get_current_owner() -> str:
    return DEFAULT_OWNER_ID
