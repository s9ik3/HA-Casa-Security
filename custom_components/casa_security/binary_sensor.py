"""Piattaforma binary_sensor: per ogni livello espone un sensore che è `on`
se e solo se TUTTE le automazioni generate per quel livello sono `on`.
"""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .coordinator import CasaSecurityCoordinator, LevelConfig

_LOGGER = logging.getLogger(__name__)


class CasaSecurityLevelStatusSensor(BinarySensorEntity):
    """Sensore `binary_sensor.<slug>_attivo`: on solo se tutte le automazioni
    del livello sono attualmente abilitate."""

    _attr_should_poll = False
    _attr_icon = "mdi:shield-check"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: CasaSecurityCoordinator,
        level: LevelConfig,
    ) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._level = level
        self._attr_unique_id = f"{DOMAIN}_{level.id}_status"
        self.entity_id = level.binary_sensor_entity_id
        self._attr_name = f"{level.name} Attivo"
        self._automation_entity_ids = [
            f"automation.{level.automation_object_id(cam)}"
            for cam in level.cameras
        ]
        self._unsub = None

    @property
    def is_on(self) -> bool:
        """True se e solo se esiste almeno un'automazione e tutte sono `on`."""
        if not self._automation_entity_ids:
            return False
        for entity_id in self._automation_entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None or state.state != "on":
                return False
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._automation_entity_ids:
            self._unsub = async_track_state_change_event(
                self.hass, self._automation_entity_ids, self._async_state_changed
            )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()

    @callback
    def _async_state_changed(self, event: Event) -> None:
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea i binary_sensor di stato per tutti i livelli correnti."""
    coordinator: CasaSecurityCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        CasaSecurityLevelStatusSensor(hass, coordinator, level)
        for level in coordinator.levels
    ]
    async_add_entities(entities)
