"""Entity id helpers for smart_venetian_blinds."""

from __future__ import annotations

from homeassistant.util import slugify


def build_entity_id(platform: str, name: str, key: str) -> str:
    """
    Build a stable, language-independent entity id.

    Home Assistant would otherwise derive the object id from the *translated*
    entity name, which makes ids differ per UI language. The slug comes from
    Home Assistant's own ``slugify`` so it only ever contains characters
    ``valid_entity_id`` accepts: a hand-rolled slug built on the word-character
    class keeps umlauts and produces an id Home Assistant rejects (e.g. a group
    called "Büro").

    Args:
        platform: The entity platform, e.g. ``select``.
        name: The window group's title, or the cover's name for per-cover entities.
        key: The entity description key.

    Returns:
        A valid entity id.
    """
    return f"{platform}.{slugify(name)}_{key}"
