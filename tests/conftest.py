"""Fixture condivise per i test di Casa Security."""
from __future__ import annotations

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Abilita il caricamento delle custom integration nei test.

    Richiesto da pytest-homeassistant-custom-component affinché
    `custom_components/casa_security` sia risolvibile durante i test.
    """
    yield
