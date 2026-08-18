"""Integrazione Casa Security per Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import CasaSecurityCoordinator
from .dashboard import async_remove_dashboard, async_sync_dashboard

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Inizializza la config entry: coordinator, piattaforme, dashboard."""
    coordinator = CasaSecurityCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # La dashboard va sincronizzata dopo che le piattaforme hanno registrato
    # le entità, così le card puntano a entity_id realmente esistenti.
    await async_sync_dashboard(hass, coordinator)

    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    return True


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Ricarica interamente la config entry quando le Options cambiano.

    Il reload garantisce che add/edit/remove di un livello propaghi in modo
    coerente a automazioni, script, binary_sensor e dashboard, senza dover
    gestire manualmente ogni possibile diff.
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Scarica la config entry: rimuove le piattaforme (le entità restano
    nel registry finché la config entry non viene rimossa del tutto, come da
    comportamento standard di Home Assistant)."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Pulizia completa quando l'integrazione viene rimossa: dashboard e
    label create ad-hoc che non sono più referenziate da altro."""
    await async_remove_dashboard(hass)
