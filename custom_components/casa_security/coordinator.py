"""Coordinator per Casa Security.

Il coordinator non fa polling di dati esterni: la sua responsabilità è tenere
una vista aggiornata e "risolta" (con slug deterministici, label create/riusate,
ecc.) dei livelli di sicurezza definiti nella config entry, e notificare i
listener (piattaforme automation/script/binary_sensor + dashboard) quando la
configurazione cambia, cosicché tutte le entità dinamiche vengano
create/aggiornate/rimosse in modo coerente.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import slugify

from .const import (
    CONF_BASE_PATH,
    CONF_CAM_CAMERA_ENTITY,
    CONF_CAM_ID,
    CONF_CAM_NAME,
    CONF_CAM_TRIGGER_ENTITY,
    CONF_CAM_VIDEO_DURATION,
    CONF_CAM_VIDEO_LOOKBACK,
    CONF_LEVEL_CAMERAS,
    CONF_LEVEL_DEPENDS_ON,
    CONF_LEVEL_ICON_OFF,
    CONF_LEVEL_ICON_ON,
    CONF_LEVEL_ID,
    CONF_LEVEL_LABEL_ID,
    CONF_LEVEL_NAME,
    CONF_LEVELS,
    DEFAULT_BASE_PATH,
    DEFAULT_ICON_OFF,
    DEFAULT_ICON_ON,
    DEFAULT_VIDEO_DURATION,
    DEFAULT_VIDEO_LOOKBACK,
    DOMAIN,
    LABEL_COLOR_DEFAULT,
    LABEL_ICON_DEFAULT,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Configurazione di una singola telecamera all'interno di un livello."""

    id: str
    trigger_entity: str
    camera_entity: str
    camera_name: str
    video_duration: int = DEFAULT_VIDEO_DURATION
    video_lookback: int = DEFAULT_VIDEO_LOOKBACK


@dataclass
class LevelConfig:
    """Configurazione risolta di un livello di sicurezza."""

    id: str
    name: str
    slug: str
    label_id: str
    icon_on: str = DEFAULT_ICON_ON
    icon_off: str = DEFAULT_ICON_OFF
    depends_on: str | None = None
    cameras: list[CameraConfig] = field(default_factory=list)

    @property
    def script_entity_id(self) -> str:
        return f"script.{self.slug}"

    @property
    def binary_sensor_object_id(self) -> str:
        return f"{self.slug}_attivo"

    @property
    def binary_sensor_entity_id(self) -> str:
        return f"binary_sensor.{self.binary_sensor_object_id}"

    def automation_unique_id(self, camera_id: str) -> str:
        return f"{DOMAIN}_{self.id}_{camera_id}_automation"

    def automation_object_id(self, camera: CameraConfig) -> str:
        cam_slug = slugify(camera.camera_name) or camera.id
        return f"{self.slug}_{cam_slug}"


def _unique_slug(name: str, taken: set[str]) -> str:
    """Genera uno slug deterministico da `name`, univoco rispetto a `taken`."""
    base = slugify(name) or "livello"
    slug = base
    counter = 2
    while slug in taken:
        slug = f"{base}_{counter}"
        counter += 1
    taken.add(slug)
    return slug


class CasaSecurityCoordinator(DataUpdateCoordinator[list[LevelConfig]]):
    """Tiene la vista risolta dei livelli di sicurezza e gestisce le label."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Nessun polling: l'aggiornamento è guidato dai listener della
            # config entry (async_update_listener in __init__.py).
            update_interval=None,
        )
        self.hass = hass
        self.entry = entry
        self.base_path: str = entry.options.get(
            CONF_BASE_PATH, entry.data.get(CONF_BASE_PATH, DEFAULT_BASE_PATH)
        )
        self.levels: list[LevelConfig] = []

    async def _async_update_data(self) -> list[LevelConfig]:
        """Ricostruisce la vista risolta dei livelli dalla config entry."""
        options = self.entry.options
        self.base_path = options.get(
            CONF_BASE_PATH, self.entry.data.get(CONF_BASE_PATH, DEFAULT_BASE_PATH)
        )
        raw_levels = options.get(CONF_LEVELS, [])

        label_reg = lr.async_get(self.hass)
        taken_slugs: set[str] = set()
        resolved: list[LevelConfig] = []

        for raw in raw_levels:
            name = raw[CONF_LEVEL_NAME]
            slug = _unique_slug(name, taken_slugs)

            label_id = raw.get(CONF_LEVEL_LABEL_ID)
            label_entry = None
            if label_id:
                label_entry = label_reg.async_get_label(label_id)
            if label_entry is None:
                # La label configurata non esiste (o non era stata creata):
                # la creiamo/recuperiamo per nome così `automation.toggle`
                # con `target: label_id:` funzioni sempre.
                label_entry = label_reg.async_get_label_by_name(
                    name
                ) or label_reg.async_create(
                    name=name,
                    icon=LABEL_ICON_DEFAULT,
                    color=LABEL_COLOR_DEFAULT,
                )
            label_id = label_entry.label_id

            cameras = [
                CameraConfig(
                    id=cam[CONF_CAM_ID],
                    trigger_entity=cam[CONF_CAM_TRIGGER_ENTITY],
                    camera_entity=cam[CONF_CAM_CAMERA_ENTITY],
                    camera_name=cam[CONF_CAM_NAME],
                    video_duration=cam.get(
                        CONF_CAM_VIDEO_DURATION, DEFAULT_VIDEO_DURATION
                    ),
                    video_lookback=cam.get(
                        CONF_CAM_VIDEO_LOOKBACK, DEFAULT_VIDEO_LOOKBACK
                    ),
                )
                for cam in raw.get(CONF_LEVEL_CAMERAS, [])
            ]

            resolved.append(
                LevelConfig(
                    id=raw[CONF_LEVEL_ID],
                    name=name,
                    slug=slug,
                    label_id=label_id,
                    icon_on=raw.get(CONF_LEVEL_ICON_ON, DEFAULT_ICON_ON),
                    icon_off=raw.get(CONF_LEVEL_ICON_OFF, DEFAULT_ICON_OFF),
                    depends_on=raw.get(CONF_LEVEL_DEPENDS_ON),
                    cameras=cameras,
                )
            )

        self.levels = resolved
        return resolved

    def get_level(self, level_id: str) -> LevelConfig | None:
        for level in self.levels:
            if level.id == level_id:
                return level
        return None
