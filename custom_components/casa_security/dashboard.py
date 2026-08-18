"""Gestione della dashboard Lovelace dedicata all'integrazione.

Usa l'API storage-mode di Lovelace (`lovelace.dashboards` collection) per
creare/aggiornare in modo idempotente una dashboard con una view contenente
una `custom:button-card` per livello. Non viene scritto alcun file YAML: la
config della dashboard vive nello storage interno di Home Assistant, esatto
analogo storage-mode di quanto farebbe l'utente da UI.
"""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .const import (
    DASHBOARD_ICON,
    DASHBOARD_TITLE,
    DASHBOARD_URL_PATH,
    DASHBOARD_VIEW_PATH,
    DASHBOARD_VIEW_TITLE,
)
from .coordinator import CasaSecurityCoordinator, LevelConfig

_LOGGER = logging.getLogger(__name__)


def _build_card(level: LevelConfig) -> dict:
    """Costruisce la config della `custom:button-card` per un livello,
    replicando fedelmente stile e comportamento dello YAML di riferimento."""
    entity_id = level.binary_sensor_entity_id

    if level.depends_on:
        dep_entity = f"binary_sensor.{level.depends_on}_attivo"
        # NB: `level.depends_on` qui è già uno slug di livello (risolto dal
        # config/options flow prima di essere salvato); vedi config_flow.py.
        tap_condition = (
            "if (states['%s'] && states['%s'].state == 'on') "
            "{ return 'call-service'; } return 'none';"
        ) % (dep_entity, dep_entity)
    else:
        tap_condition = "return 'call-service';"

    return {
        "type": "custom:button-card",
        "entity": entity_id,
        "name": level.name,
        "show_state": True,
        "icon": (
            "[[[\n"
            f"  if (states['{entity_id}'].state == 'on') return '{level.icon_on}';\n"
            f"  else return '{level.icon_off}';\n"
            "]]]"
        ),
        "tap_action": {
            "action": f"[[[\n  {tap_condition}\n]]]",
            "service": level.script_entity_id,
        },
        "styles": {
            "card": [
                {"font-size": "14px"},
                {"padding": "14px"},
                {"border-radius": "12px"},
                {"box-shadow": "0px 2px 4px rgba(0,0,0,0.2)"},
                {"border": "2px solid"},
                {
                    "border-color": (
                        "[[[\n"
                        f"  if (states['{entity_id}'].state == 'on') "
                        "return 'var(--success-color)';\n"
                        "  else return 'var(--error-color)';\n"
                        "]]]"
                    )
                },
                {"background-color": "var(--card-background-color)"},
            ],
            "icon": [{"width": "25%"}, {"color": "var(--primary-text-color)"}],
            "name": [{"font-weight": "bold"}, {"font-size": "15px"}],
            "state": [{"font-size": "13px"}, {"color": "var(--secondary-text-color)"}],
        },
    }


def _build_view(levels: list[LevelConfig]) -> dict:
    """Costruisce la view a griglia 2 colonne con una card per livello."""
    return {
        "path": DASHBOARD_VIEW_PATH,
        "title": DASHBOARD_VIEW_TITLE,
        "icon": DASHBOARD_ICON,
        "cards": [
            {
                "type": "grid",
                "columns": 2,
                "cards": [_build_card(level) for level in levels],
            }
        ],
    }


def _get_dashboards_collection(hass: HomeAssistant):
    """Recupera la collection delle dashboard storage-mode, se disponibile."""
    lovelace_data = hass.data.get("lovelace")
    if lovelace_data is None:
        return None
    # In HA moderne `hass.data["lovelace"]` è un oggetto con attributo
    # `dashboards_collection`; in versioni più vecchie può essere un dict.
    return getattr(lovelace_data, "dashboards_collection", None)


async def async_sync_dashboard(
    hass: HomeAssistant, coordinator: CasaSecurityCoordinator
) -> None:
    """Crea la dashboard dedicata se non esiste, e aggiorna (senza duplicare)
    la view dei livelli. Le card dei livelli rimossi spariscono perché la
    view viene interamente ricostruita dallo stato corrente dei livelli.
    """
    collection = _get_dashboards_collection(hass)
    if collection is None:
        _LOGGER.warning(
            "Lovelace storage mode non disponibile: impossibile generare "
            "automaticamente la dashboard di Casa Security. Puoi comunque "
            "usare le entità generate (automation/script/binary_sensor) "
            "in una dashboard manuale."
        )
        return

    existing = None
    for item in collection.async_items():
        if item.get("url_path") == DASHBOARD_URL_PATH:
            existing = item
            break

    if existing is None:
        existing = await collection.async_create_item(
            {
                "url_path": DASHBOARD_URL_PATH,
                "title": DASHBOARD_TITLE,
                "icon": DASHBOARD_ICON,
                "show_in_sidebar": True,
                "require_admin": False,
                "mode": "storage",
            }
        )

    dashboard_id = existing["id"]
    store = hass.data["lovelace"].dashboards.get(dashboard_id)
    if store is None:
        _LOGGER.warning("Impossibile accedere allo store della dashboard %s", dashboard_id)
        return

    config = await store.async_load(False) or {"views": []}
    views = config.get("views", [])

    new_view = _build_view(coordinator.levels)

    updated = False
    for idx, view in enumerate(views):
        if view.get("path") == DASHBOARD_VIEW_PATH:
            views[idx] = new_view
            updated = True
            break
    if not updated:
        views.append(new_view)

    config["views"] = views
    await store.async_save(config)


async def async_remove_dashboard(hass: HomeAssistant) -> None:
    """Rimuove la dashboard dedicata quando l'integrazione viene disinstallata."""
    collection = _get_dashboards_collection(hass)
    if collection is None:
        return

    existing = None
    for item in collection.async_items():
        if item.get("url_path") == DASHBOARD_URL_PATH:
            existing = item
            break

    if existing is not None:
        await collection.async_delete_item(existing["id"])
