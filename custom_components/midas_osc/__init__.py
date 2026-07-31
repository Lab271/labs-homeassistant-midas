# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Schuberg Philis / Lab271
"""The Midas OSC integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_INPUTS,
    CONF_LOCAL_PORT,
    CONF_OUTPUT_DEFAULT,
    CONF_OUTPUTS,
    DEFAULT_FADER_LEVEL,
    DOMAIN,
    PLATFORMS,
)
from .hub import MidasOSCHub

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a pre-topology (v1) entry.

    v1 entries stored only connection details; the entity topology was
    hardcoded. There is no way to recover which rooms and sources a given
    install used, so seed an empty topology and let the user define theirs via
    the Configure menu. The entry loads with no entities until they do.
    """
    if entry.version > 1:
        return False

    _LOGGER.warning(
        "Migrating %s from v1: entity topology is now configured in the UI. "
        "Open Configure to add your outputs and inputs. Entities from v1 have "
        "been replaced and their old entries can be removed",
        entry.title,
    )
    hass.config_entries.async_update_entry(
        entry,
        options={
            CONF_OUTPUTS: [],
            CONF_INPUTS: [],
            CONF_OUTPUT_DEFAULT: DEFAULT_FADER_LEVEL,
            **dict(entry.options),
        },
        version=2,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Midas OSC from a config entry."""
    _LOGGER.debug("Setting up Midas OSC entry: %s", entry.title)

    hub = MidasOSCHub(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        local_port=entry.data[CONF_LOCAL_PORT],
    )

    try:
        await hub.start()
    except OSError as err:
        # Most likely the local port is already bound by another entry or app.
        raise ConfigEntryNotReady(
            f"Could not bind local port {entry.data[CONF_LOCAL_PORT]}: {err}"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        # Never leave the UDP port bound behind a failed setup.
        hass.data[DOMAIN].pop(entry.entry_id, None)
        await hub.stop()
        raise

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Midas OSC config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hub: MidasOSCHub = hass.data[DOMAIN].pop(entry.entry_id)
        await hub.stop()
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its connection or topology changes."""
    await hass.config_entries.async_reload(entry.entry_id)
