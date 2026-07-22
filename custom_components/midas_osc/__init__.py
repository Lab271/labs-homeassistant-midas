# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Schuberg Philis / Lab271
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from . import number

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Midas OSC from a config entry."""
    name = entry.data["name"]
    _LOGGER.info("Setting up Midas OSC entry: %s", name)

    # Store data in hass
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"name": name}

    # Forward entry setups for platforms (light and number)
    await hass.config_entries.async_forward_entry_setups(entry, ["number"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Midas OSC config entry."""
    await hass.config_entries.async_unload_platforms(entry, ["number"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True