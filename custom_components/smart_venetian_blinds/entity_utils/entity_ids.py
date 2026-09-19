"""String helpers for smart_venetian_blinds."""

from __future__ import annotations

from homeassistant.util import slugify


def build_entity_id(platform: str, group_title: str, key: str) -> str:
    """
    Build a stable, language-independent entity id for a window group entity.

    Home Assistant would otherwise derive the object id from the *translated*
    entity name, which makes ids differ per UI language. It also uses its own
    slugify, which folds umlauts to ASCII — the local ``slugify_name`` keeps them
    and would produce an entity id Home Assistant rejects (e.g. a group called
    "Büro").

    Args:
        platform: The entity platform, e.g. ``select``.
        group_title: The window group's title.
        key: The entity description key.

    Returns:
        A valid entity id.
    """
    return f"{platform}.{slugify(group_title)}_{key}"
