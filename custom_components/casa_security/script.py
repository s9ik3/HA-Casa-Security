"""Piattaforma script: genera uno script "toggle" per livello che esegue
`automation.toggle` su tutte le automazioni con la label del livello.
"""
from __future__ import annotations

import logging

from homeassistant.components.script import ScriptEntity
from homeassistant.components.script.config import async_validate_config_item
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CasaSecurityCoordinator, LevelConfig

_LOGGER = logging.getLogger(__name__)


def _build_script_config(level: LevelConfig) -> dict:
    """Config dello script equivalente allo YAML `attiva_sicurezza_dinamica`,
    con target sulla label del livello invece che su una label hardcoded."""
    return {
        "alias": f"Attiva {level.name}",
        "mode": "single",
        "sequence": [
            {
                "target": {"label_id": level.label_id},
                "action": "automation.toggle",
            }
        ],
    }


class CasaSecurityScriptEntity(ScriptEntity):
    """Script toggle generato dinamicamente per un livello."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: CasaSecurityCoordinator,
        level: LevelConfig,
        object_id: str,
        raw_config: dict,
    ) -> None:
        super().__init__(hass, object_id, raw_config["alias"], raw_config, None)
        self._attr_unique_id = f"{DOMAIN}_{level.id}_script"
        self.entity_id = f"script.{object_id}"
        self._coordinator = coordinator
        self._level = level


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea gli script toggle per tutti i livelli correnti."""
    coordinator: CasaSecurityCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[CasaSecurityScriptEntity] = []
    for level in coordinator.levels:
        raw_config = _build_script_config(level)
        validated = await async_validate_config_item(hass, level.slug, raw_config)
        entities.append(
            CasaSecurityScriptEntity(
                hass, coordinator, level, level.slug, validated
            )
        )

    async_add_entities(entities)
