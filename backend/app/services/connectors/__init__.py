"""Provider registry — connections.py and automation.py dispatch to the
right connector module by Connection.provider without needing a branch
per provider. Adding a new provider is: write the module (same interface
as base.py documents), add it here."""
from __future__ import annotations

from types import ModuleType

from app.services.connectors import aws, github

CONNECTORS: dict[str, ModuleType] = {
    "GITHUB": github,
    "AWS": aws,
}


def all_check_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    for module in CONNECTORS.values():
        labels.update(module.CHECK_LABELS)
    return labels
