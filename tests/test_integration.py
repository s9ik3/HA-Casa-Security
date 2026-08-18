"""Test di integrazione per Casa Security.

Copre:
- creazione della config entry;
- aggiunta di un livello con 1 telecamera via Options Flow (simulata
  scrivendo direttamente le options, equivalente all'esito di un flow
  completato);
- generazione delle entità automation/script/binary_sensor con gli
  entity_id attesi;
- toggle dello script che accende/spegne le automazioni tramite label.
"""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import label_registry as lr

from custom_components.casa_security.const import (
    CONF_BASE_PATH,
    CONF_CAM_CAMERA_ENTITY,
    CONF_CAM_ID,
    CONF_CAM_NAME,
    CONF_CAM_TRIGGER_ENTITY,
    CONF_LEVEL_CAMERAS,
    CONF_LEVEL_ICON_OFF,
    CONF_LEVEL_ICON_ON,
    CONF_LEVEL_ID,
    CONF_LEVEL_LABEL_ID,
    CONF_LEVEL_NAME,
    CONF_LEVELS,
    DEFAULT_BASE_PATH,
    DOMAIN,
)


async def _setup_binary_sensor_and_camera_stubs(hass: HomeAssistant) -> None:
    """Registra gli stati minimi necessari (sensore trigger e camera) così
    che gli EntitySelector/EntitySelectorConfig referenziati esistano."""
    hass.states.async_set("binary_sensor.cancello_movimento", "off")
    hass.states.async_set("camera.cancello", "idle")


async def _create_entry_with_one_level(hass: HomeAssistant) -> MockConfigEntry:
    await _setup_binary_sensor_and_camera_stubs(hass)

    label_reg = lr.async_get(hass)
    label = label_reg.async_create(name="Sicurezza Perimetro")

    level = {
        CONF_LEVEL_ID: "level-1",
        CONF_LEVEL_NAME: "Sicurezza Perimetro",
        CONF_LEVEL_LABEL_ID: label.label_id,
        CONF_LEVEL_ICON_ON: "mdi:shield-home",
        CONF_LEVEL_ICON_OFF: "mdi:shield-off",
        CONF_LEVEL_CAMERAS: [
            {
                CONF_CAM_ID: "cam-1",
                CONF_CAM_TRIGGER_ENTITY: "binary_sensor.cancello_movimento",
                CONF_CAM_CAMERA_ENTITY: "camera.cancello",
                CONF_CAM_NAME: "Cancello",
            }
        ],
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Casa Security",
        data={},
        options={CONF_BASE_PATH: DEFAULT_BASE_PATH, CONF_LEVELS: [level]},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.asyncio
async def test_setup_entry_creates_expected_entities(hass: HomeAssistant) -> None:
    """La config entry con un livello e una telecamera genera le entità
    automation/script/binary_sensor con gli entity_id attesi."""
    entry = await _create_entry_with_one_level(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    automation_state = hass.states.get(
        "automation.sicurezza_perimetro_cancello"
    )
    assert automation_state is not None

    script_state = hass.states.get("script.sicurezza_perimetro")
    assert script_state is not None

    sensor_state = hass.states.get("binary_sensor.sicurezza_perimetro_attivo")
    assert sensor_state is not None


@pytest.mark.asyncio
async def test_binary_sensor_on_only_if_all_automations_on(
    hass: HomeAssistant,
) -> None:
    """Il binary_sensor di livello è `on` solo se l'automazione (unica, in
    questo test) è `on`, e torna `off` se viene disabilitata."""
    entry = await _create_entry_with_one_level(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    automation_entity_id = "automation.sicurezza_perimetro_cancello"
    sensor_entity_id = "binary_sensor.sicurezza_perimetro_attivo"

    # L'automazione è abilitata di default alla creazione -> sensore on.
    assert hass.states.get(automation_entity_id).state == "on"
    assert hass.states.get(sensor_entity_id).state == "on"

    await hass.services.async_call(
        "automation",
        "turn_off",
        {"entity_id": automation_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(automation_entity_id).state == "off"
    assert hass.states.get(sensor_entity_id).state == "off"


@pytest.mark.asyncio
async def test_script_toggle_uses_label_target(hass: HomeAssistant) -> None:
    """Chiamare lo script del livello esegue `automation.toggle` sulla label
    del livello, invertendo lo stato dell'automazione associata."""
    entry = await _create_entry_with_one_level(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    automation_entity_id = "automation.sicurezza_perimetro_cancello"
    assert hass.states.get(automation_entity_id).state == "on"

    await hass.services.async_call(
        "script",
        "sicurezza_perimetro",
        {},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(automation_entity_id).state == "off"

    await hass.services.async_call(
        "script",
        "sicurezza_perimetro",
        {},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(automation_entity_id).state == "on"
