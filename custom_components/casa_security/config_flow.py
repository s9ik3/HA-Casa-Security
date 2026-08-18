"""Config Flow e Options Flow per Casa Security.

Tutta la configurazione (livelli, telecamere per livello) avviene da UI,
niente YAML manuale. L'Options Flow espone un menu ripetibile per il CRUD
completo dei livelli e, all'interno di ciascun livello, un sotto-flow
ripetibile per il CRUD delle telecamere associate.
"""
from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

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
    MAX_VIDEO_DURATION,
    MAX_VIDEO_LOOKBACK,
    MIN_VIDEO_DURATION,
    MIN_VIDEO_LOOKBACK,
    STEP_VIDEO_DURATION,
    STEP_VIDEO_LOOKBACK,
)


class CasaSecurityConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow iniziale: crea la singola config entry dell'integrazione."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        # Una sola istanza: l'integrazione è pensata come singolo hub che
        # gestisce N livelli internamente (via Options Flow).
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="Casa Security",
                data={},
                options={
                    CONF_BASE_PATH: user_input[CONF_BASE_PATH],
                    CONF_LEVELS: [],
                },
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BASE_PATH, default=DEFAULT_BASE_PATH
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "CasaSecurityOptionsFlow":
        return CasaSecurityOptionsFlow(config_entry)


class CasaSecurityOptionsFlow(config_entries.OptionsFlow):
    """Options Flow: menu ripetibile per CRUD dei livelli e delle telecamere."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        # Copia di lavoro delle options correnti, modificata step-by-step e
        # persistita solo quando l'utente conferma/esce dal menu principale.
        self._levels: list[dict[str, Any]] = [
            dict(level) for level in config_entry.options.get(CONF_LEVELS, [])
        ]
        self._base_path: str = config_entry.options.get(
            CONF_BASE_PATH, DEFAULT_BASE_PATH
        )
        # Stato temporaneo mentre si crea/modifica un livello o una telecamera.
        self._current_level: dict[str, Any] | None = None
        self._current_level_index: int | None = None
        self._current_camera: dict[str, Any] | None = None
        self._current_camera_index: int | None = None

    # ---------------------------------------------------------------- menu --
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "global_settings",
                "add_level",
                "edit_level",
                "remove_level",
                "finish",
            ],
        )

    async def async_step_global_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            self._base_path = user_input[CONF_BASE_PATH]
            return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BASE_PATH, default=self._base_path
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="global_settings", data_schema=schema)

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        return self.async_create_entry(
            title="",
            data={
                CONF_BASE_PATH: self._base_path,
                CONF_LEVELS: self._levels,
            },
        )

    # ---------------------------------------------------------- add/edit level --
    def _level_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        other_levels = [
            l for l in self._levels if l.get(CONF_LEVEL_ID) != defaults.get(CONF_LEVEL_ID)
        ]
        depends_options = [
            selector.SelectOptionDict(value=l[CONF_LEVEL_ID], label=l[CONF_LEVEL_NAME])
            for l in other_levels
        ]

        return vol.Schema(
            {
                vol.Required(
                    CONF_LEVEL_NAME, default=defaults.get(CONF_LEVEL_NAME, "")
                ): selector.TextSelector(),
                vol.Required(
                    CONF_LEVEL_LABEL_ID, default=defaults.get(CONF_LEVEL_LABEL_ID)
                ): selector.LabelSelector(
                    selector.LabelSelectorConfig(multiple=False)
                ),
                vol.Optional(
                    CONF_LEVEL_ICON_ON,
                    default=defaults.get(CONF_LEVEL_ICON_ON, DEFAULT_ICON_ON),
                ): selector.IconSelector(),
                vol.Optional(
                    CONF_LEVEL_ICON_OFF,
                    default=defaults.get(CONF_LEVEL_ICON_OFF, DEFAULT_ICON_OFF),
                ): selector.IconSelector(),
                vol.Optional(
                    CONF_LEVEL_DEPENDS_ON,
                    description={"suggested_value": defaults.get(CONF_LEVEL_DEPENDS_ON)},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=depends_options, mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
            }
        )

    async def async_step_add_level(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            self._current_level = {
                CONF_LEVEL_ID: str(uuid.uuid4()),
                CONF_LEVEL_NAME: user_input[CONF_LEVEL_NAME],
                CONF_LEVEL_LABEL_ID: user_input[CONF_LEVEL_LABEL_ID],
                CONF_LEVEL_ICON_ON: user_input.get(
                    CONF_LEVEL_ICON_ON, DEFAULT_ICON_ON
                ),
                CONF_LEVEL_ICON_OFF: user_input.get(
                    CONF_LEVEL_ICON_OFF, DEFAULT_ICON_OFF
                ),
                CONF_LEVEL_DEPENDS_ON: user_input.get(CONF_LEVEL_DEPENDS_ON),
                CONF_LEVEL_CAMERAS: [],
            }
            self._current_level_index = None
            return await self.async_step_camera_menu()

        return self.async_show_form(
            step_id="add_level", data_schema=self._level_schema({})
        )

    async def async_step_edit_level(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if not self._levels:
            return self.async_abort(reason="no_levels")

        if user_input is not None and CONF_LEVEL_ID in user_input:
            index = next(
                i
                for i, l in enumerate(self._levels)
                if l[CONF_LEVEL_ID] == user_input[CONF_LEVEL_ID]
            )
            self._current_level_index = index
            self._current_level = dict(self._levels[index])
            return await self.async_step_edit_level_form()

        options = [
            selector.SelectOptionDict(value=l[CONF_LEVEL_ID], label=l[CONF_LEVEL_NAME])
            for l in self._levels
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_LEVEL_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.LIST
                    )
                )
            }
        )
        return self.async_show_form(step_id="edit_level", data_schema=schema)

    async def async_step_edit_level_form(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        assert self._current_level is not None

        if user_input is not None:
            self._current_level.update(
                {
                    CONF_LEVEL_NAME: user_input[CONF_LEVEL_NAME],
                    CONF_LEVEL_LABEL_ID: user_input[CONF_LEVEL_LABEL_ID],
                    CONF_LEVEL_ICON_ON: user_input.get(
                        CONF_LEVEL_ICON_ON, DEFAULT_ICON_ON
                    ),
                    CONF_LEVEL_ICON_OFF: user_input.get(
                        CONF_LEVEL_ICON_OFF, DEFAULT_ICON_OFF
                    ),
                    CONF_LEVEL_DEPENDS_ON: user_input.get(CONF_LEVEL_DEPENDS_ON),
                }
            )
            return await self.async_step_camera_menu()

        return self.async_show_form(
            step_id="edit_level_form",
            data_schema=self._level_schema(self._current_level),
        )

    async def async_step_remove_level(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if not self._levels:
            return self.async_abort(reason="no_levels")

        if user_input is not None and CONF_LEVEL_ID in user_input:
            self._levels = [
                l
                for l in self._levels
                if l[CONF_LEVEL_ID] != user_input[CONF_LEVEL_ID]
            ]
            return await self.async_step_init()

        options = [
            selector.SelectOptionDict(value=l[CONF_LEVEL_ID], label=l[CONF_LEVEL_NAME])
            for l in self._levels
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_LEVEL_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.LIST
                    )
                )
            }
        )
        return self.async_show_form(step_id="remove_level", data_schema=schema)

    # ------------------------------------------------------- camera sub-flow --
    async def async_step_camera_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Sotto-menu ripetibile per gestire le telecamere del livello
        correntemente in creazione/modifica (`self._current_level`)."""
        return self.async_show_menu(
            step_id="camera_menu",
            menu_options=[
                "add_camera",
                "edit_camera",
                "remove_camera",
                "save_level",
            ],
        )

    def _camera_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_CAM_TRIGGER_ENTITY,
                    default=defaults.get(CONF_CAM_TRIGGER_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Required(
                    CONF_CAM_CAMERA_ENTITY,
                    default=defaults.get(CONF_CAM_CAMERA_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="camera")
                ),
                vol.Required(
                    CONF_CAM_NAME, default=defaults.get(CONF_CAM_NAME, "")
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_CAM_VIDEO_DURATION,
                    default=defaults.get(
                        CONF_CAM_VIDEO_DURATION, DEFAULT_VIDEO_DURATION
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_VIDEO_DURATION,
                        max=MAX_VIDEO_DURATION,
                        step=STEP_VIDEO_DURATION,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_CAM_VIDEO_LOOKBACK,
                    default=defaults.get(
                        CONF_CAM_VIDEO_LOOKBACK, DEFAULT_VIDEO_LOOKBACK
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_VIDEO_LOOKBACK,
                        max=MAX_VIDEO_LOOKBACK,
                        step=STEP_VIDEO_LOOKBACK,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

    async def async_step_add_camera(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        assert self._current_level is not None

        if user_input is not None:
            camera = {
                CONF_CAM_ID: str(uuid.uuid4()),
                CONF_CAM_TRIGGER_ENTITY: user_input[CONF_CAM_TRIGGER_ENTITY],
                CONF_CAM_CAMERA_ENTITY: user_input[CONF_CAM_CAMERA_ENTITY],
                CONF_CAM_NAME: user_input[CONF_CAM_NAME],
                CONF_CAM_VIDEO_DURATION: user_input.get(
                    CONF_CAM_VIDEO_DURATION, DEFAULT_VIDEO_DURATION
                ),
                CONF_CAM_VIDEO_LOOKBACK: user_input.get(
                    CONF_CAM_VIDEO_LOOKBACK, DEFAULT_VIDEO_LOOKBACK
                ),
            }
            self._current_level[CONF_LEVEL_CAMERAS].append(camera)
            return await self.async_step_camera_menu()

        return self.async_show_form(
            step_id="add_camera", data_schema=self._camera_schema({})
        )

    async def async_step_edit_camera(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        assert self._current_level is not None
        cameras = self._current_level[CONF_LEVEL_CAMERAS]

        if not cameras:
            return self.async_abort(reason="no_cameras")

        if user_input is not None and CONF_CAM_ID in user_input:
            index = next(
                i for i, c in enumerate(cameras) if c[CONF_CAM_ID] == user_input[CONF_CAM_ID]
            )
            self._current_camera_index = index
            return await self.async_step_edit_camera_form()

        options = [
            selector.SelectOptionDict(value=c[CONF_CAM_ID], label=c[CONF_CAM_NAME])
            for c in cameras
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_CAM_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.LIST
                    )
                )
            }
        )
        return self.async_show_form(step_id="edit_camera", data_schema=schema)

    async def async_step_edit_camera_form(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        assert self._current_level is not None
        assert self._current_camera_index is not None
        cameras = self._current_level[CONF_LEVEL_CAMERAS]

        if user_input is not None:
            cameras[self._current_camera_index].update(
                {
                    CONF_CAM_TRIGGER_ENTITY: user_input[CONF_CAM_TRIGGER_ENTITY],
                    CONF_CAM_CAMERA_ENTITY: user_input[CONF_CAM_CAMERA_ENTITY],
                    CONF_CAM_NAME: user_input[CONF_CAM_NAME],
                    CONF_CAM_VIDEO_DURATION: user_input.get(
                        CONF_CAM_VIDEO_DURATION, DEFAULT_VIDEO_DURATION
                    ),
                    CONF_CAM_VIDEO_LOOKBACK: user_input.get(
                        CONF_CAM_VIDEO_LOOKBACK, DEFAULT_VIDEO_LOOKBACK
                    ),
                }
            )
            self._current_camera_index = None
            return await self.async_step_camera_menu()

        defaults = cameras[self._current_camera_index]
        return self.async_show_form(
            step_id="edit_camera_form", data_schema=self._camera_schema(defaults)
        )

    async def async_step_remove_camera(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        assert self._current_level is not None
        cameras = self._current_level[CONF_LEVEL_CAMERAS]

        if not cameras:
            return self.async_abort(reason="no_cameras")

        if user_input is not None and CONF_CAM_ID in user_input:
            self._current_level[CONF_LEVEL_CAMERAS] = [
                c for c in cameras if c[CONF_CAM_ID] != user_input[CONF_CAM_ID]
            ]
            return await self.async_step_camera_menu()

        options = [
            selector.SelectOptionDict(value=c[CONF_CAM_ID], label=c[CONF_CAM_NAME])
            for c in cameras
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_CAM_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.LIST
                    )
                )
            }
        )
        return self.async_show_form(step_id="remove_camera", data_schema=schema)

    async def async_step_save_level(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Persiste il livello corrente (nuovo o modificato) nella lista di
        lavoro e torna al menu principale."""
        assert self._current_level is not None

        if self._current_level_index is not None:
            self._levels[self._current_level_index] = self._current_level
        else:
            self._levels.append(self._current_level)

        self._current_level = None
        self._current_level_index = None
        self._current_camera = None
        self._current_camera_index = None

        return await self.async_step_init()
