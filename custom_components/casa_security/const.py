"""Costanti per l'integrazione Casa Security."""
from __future__ import annotations

DOMAIN = "casa_security"
PLATFORMS = ["automation", "script", "binary_sensor"]

# --- Config entry data / options keys -------------------------------------------------
CONF_BASE_PATH = "base_path"
CONF_LEVELS = "levels"

DEFAULT_BASE_PATH = "/media/VideoTelecamere/Volume/HAOS/SORVEGLIANZA"

# --- Level schema keys -------------------------------------------------------------
CONF_LEVEL_ID = "id"
CONF_LEVEL_NAME = "name"
CONF_LEVEL_LABEL_ID = "label_id"
CONF_LEVEL_ICON_ON = "icon_on"
CONF_LEVEL_ICON_OFF = "icon_off"
CONF_LEVEL_DEPENDS_ON = "depends_on"
CONF_LEVEL_CAMERAS = "cameras"

DEFAULT_ICON_ON = "mdi:shield-home"
DEFAULT_ICON_OFF = "mdi:shield-off"

# --- Camera (per livello) schema keys -----------------------------------------------
CONF_CAM_ID = "id"
CONF_CAM_TRIGGER_ENTITY = "trigger_entity"
CONF_CAM_CAMERA_ENTITY = "camera_entity"
CONF_CAM_NAME = "camera_name"
CONF_CAM_VIDEO_DURATION = "video_duration"
CONF_CAM_VIDEO_LOOKBACK = "video_lookback"

DEFAULT_VIDEO_DURATION = 30
DEFAULT_VIDEO_LOOKBACK = 10
MIN_VIDEO_DURATION = 5
MAX_VIDEO_DURATION = 120
STEP_VIDEO_DURATION = 5
MIN_VIDEO_LOOKBACK = 0
MAX_VIDEO_LOOKBACK = 60
STEP_VIDEO_LOOKBACK = 1

# --- Dashboard -----------------------------------------------------------------------
DASHBOARD_URL_PATH = "dynamic-security"
DASHBOARD_TITLE = "Casa Security"
DASHBOARD_ICON = "mdi:shield-lock"
DASHBOARD_VIEW_PATH = "sicurezza"
DASHBOARD_VIEW_TITLE = "Sicurezza"

# --- Misc ------------------------------------------------------------------------------
SIGNAL_LEVELS_UPDATED = f"{DOMAIN}_levels_updated"
LABEL_COLOR_DEFAULT = "grey"
LABEL_ICON_DEFAULT = "mdi:shield-lock"
