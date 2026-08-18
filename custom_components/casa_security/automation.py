"""Piattaforma automation: genera dinamicamente un'automazione per ogni
telecamera di ogni livello, riproducendo 1:1 la logica del blueprint
"Notifica di sorveglianza con snapshot e video su Telegram".
"""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.automation import AutomationEntity
from homeassistant.components.automation.config import async_validate_config_item
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.trigger import async_initialize_triggers

from .const import DOMAIN
from .coordinator import CameraConfig, CasaSecurityCoordinator, LevelConfig

_LOGGER = logging.getLogger(__name__)


def _build_automation_config(
    coordinator: CasaSecurityCoordinator, level: LevelConfig, camera: CameraConfig
) -> dict:
    """Costruisce la config dell'automazione equivalente al blueprint originale.

    Rispetto allo YAML del blueprint, `base_path` e `camera_name` sono già
    risolti qui (non tramite `!input`), ma la struttura trigger/action e i
    nomi dei file restano identici.
    """
    base_path = coordinator.base_path
    friendly_name = f"Sorveglianza {level.name} - {camera.camera_name}"

    snapshot_template = (
        f"{base_path}/snapshot_{camera.camera_name}_"
        "{{ now().strftime('%Y%m%d_%H%M%S') }}.jpg"
    )
    video_template = (
        f"{base_path}/video_{camera.camera_name}_"
        "{{ now().strftime('%Y%m%d_%H%M%S') }}.mp4"
    )

    return {
        "id": level.automation_unique_id(camera.id),
        "alias": friendly_name,
        "trigger": [
            {
                "platform": "state",
                "entity_id": camera.trigger_entity,
                "to": "on",
            }
        ],
        "condition": [],
        "action": [
            {
                "parallel": [
                    {
                        "alias": "Scatta snapshot e invia foto Telegram",
                        "sequence": [
                            {
                                "action": "camera.snapshot",
                                "data": {"filename": snapshot_template},
                                "target": {"entity_id": camera.camera_entity},
                            },
                            {
                                "action": "telegram_bot.send_photo",
                                "data": {
                                    "file": snapshot_template,
                                    "caption": (
                                        f"\U0001f4f8 Foto da {camera.camera_name} "
                                        "alle {{ now().strftime('%H:%M:%S') }}"
                                    ),
                                    "authentication": "digest",
                                },
                            },
                        ],
                    },
                    {
                        "alias": "Registra il video e invia video Telegram",
                        "sequence": [
                            {
                                "action": "camera.record",
                                "data": {
                                    "filename": video_template,
                                    "duration": camera.video_duration,
                                    "lookback": camera.video_lookback,
                                },
                                "target": {"entity_id": camera.camera_entity},
                            },
                            {
                                "action": "telegram_bot.send_video",
                                "data": {
                                    "file": video_template,
                                    "caption": (
                                        f"\U0001f3a5 Video da {camera.camera_name} "
                                        "alle {{ now().strftime('%H:%M:%S') }}"
                                    ),
                                    "authentication": "digest",
                                },
                            },
                        ],
                    },
                ]
            }
        ],
        "mode": "single",
    }


class CasaSecurityAutomationEntity(AutomationEntity):
    """Automazione generata dinamicamente per una coppia (livello, telecamera)."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: CasaSecurityCoordinator,
        level: LevelConfig,
        camera: CameraConfig,
        raw_config: dict,
    ) -> None:
        automation_id = raw_config["id"]
        object_id = level.automation_object_id(camera)

        super().__init__(
            automation_id=automation_id,
            name=raw_config["alias"],
            trigger_config=raw_config["trigger"],
            cond_func=None,
            action_script=None,
            initial_state=True,
            variables=None,
            trigger_variables=None,
            raw_config=raw_config,
            blueprint_inputs=None,
            trace_config={},
        )
        self._attr_unique_id = automation_id
        self.entity_id = f"automation.{object_id}"
        self._coordinator = coordinator
        self._level = level
        self._camera = camera


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea le entità automation per tutti i livelli/telecamere correnti."""
    coordinator: CasaSecurityCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[CasaSecurityAutomationEntity] = []
    label_reg = lr.async_get(hass)

    for level in coordinator.levels:
        for camera in level.cameras:
            raw_config = _build_automation_config(coordinator, level, camera)
            validated = await async_validate_config_item(hass, raw_config)
            entity = CasaSecurityAutomationEntity(
                hass, coordinator, level, camera, validated.raw_config or raw_config
            )
            entities.append(entity)

    async_add_entities(entities)

    # Associa la label del livello a ciascuna automazione appena registrata,
    # così `target: label_id: <label>` funziona nei service call standard.
    ent_reg = er.async_get(hass)
    for level in coordinator.levels:
        for camera in level.cameras:
            object_id = level.automation_object_id(camera)
            entity_id = f"automation.{object_id}"
            reg_entry = ent_reg.async_get(entity_id)
            if reg_entry is not None and level.label_id not in reg_entry.labels:
                ent_reg.async_update_entity(
                    entity_id, labels={*reg_entry.labels, level.label_id}
                )
