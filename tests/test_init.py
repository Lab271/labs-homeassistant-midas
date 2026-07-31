# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Schuberg Philis / Lab271
"""Tests for entry setup, unload, reload and the resulting entities."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.midas_osc.const import (
    CONF_INPUTS,
    CONF_LOCAL_PORT,
    CONF_OUTPUT_DEFAULT,
    CONF_OUTPUTS,
    DOMAIN,
)

CONNECTION = {
    "name": "Midas",
    "host": "10.0.0.5",
    "port": 10023,
    CONF_LOCAL_PORT: 10024,
}

TOPOLOGY = {
    CONF_OUTPUTS: [
        {"id": "space", "label": "Space", "dca": 1, "bus": 1},
        {"id": "desks", "label": "Desks", "dca": 2, "bus": 3},
    ],
    CONF_INPUTS: [{"id": "pc", "label": "PC", "ch_l": 15, "ch_r": 16, "default": 0.75}],
    CONF_OUTPUT_DEFAULT: 0.35,
}


@pytest.fixture
def mock_hub():
    """Patch out the UDP socket, keeping start/stop observable."""
    with (
        patch(
            "custom_components.midas_osc.hub.MidasOSCHub.start", new_callable=AsyncMock
        ) as start,
        patch(
            "custom_components.midas_osc.hub.MidasOSCHub.stop", new_callable=AsyncMock
        ) as stop,
    ):
        yield start, stop


async def setup_entry(hass: HomeAssistant, options=None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Midas",
        data=CONNECTION,
        options=options if options is not None else TOPOLOGY,
        unique_id="10.0.0.5:10024",
        version=2,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_creates_faders_and_sends(hass: HomeAssistant, mock_hub):
    """Two outputs plus one input yields 2 faders + 2 sends."""
    await setup_entry(hass)

    states = hass.states.async_entity_ids("number")
    assert len(states) == 4

    assert hass.states.get("number.midas_space") is not None
    assert hass.states.get("number.midas_desks") is not None
    assert hass.states.get("number.midas_pc_space") is not None
    assert hass.states.get("number.midas_pc_desks") is not None


async def test_entities_start_at_configured_defaults(hass: HomeAssistant, mock_hub):
    await setup_entry(hass)
    assert hass.states.get("number.midas_space").state == "0.35"
    assert hass.states.get("number.midas_pc_space").state == "0.75"


async def test_all_entities_share_one_device(hass: HomeAssistant, mock_hub):
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    entry = await setup_entry(hass)

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1

    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert len(entities) == 4
    assert {e.device_id for e in entities} == {devices[0].id}


async def test_unique_ids_are_entry_scoped(hass: HomeAssistant, mock_hub):
    from homeassistant.helpers import entity_registry as er

    entry = await setup_entry(hass)
    unique_ids = {
        e.unique_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }
    assert unique_ids == {
        f"{entry.entry_id}_fader_space",
        f"{entry.entry_id}_fader_desks",
        f"{entry.entry_id}_send_pc_space",
        f"{entry.entry_id}_send_pc_desks",
    }


async def test_empty_topology_sets_up_with_no_entities(hass: HomeAssistant, mock_hub):
    """A entry with no topology must still load, not raise."""
    entry = await setup_entry(hass, options={})
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.async_entity_ids("number") == []


async def test_unload_stops_the_hub_and_clears_data(hass: HomeAssistant, mock_hub):
    _, stop = mock_hub
    entry = await setup_entry(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    stop.assert_awaited_once()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
    # HA keeps the states around, marked unavailable, rather than deleting them.
    assert all(
        hass.states.get(entity_id).state == "unavailable"
        for entity_id in hass.states.async_entity_ids("number")
    )


async def test_options_update_reloads_and_rebuilds_entities(
    hass: HomeAssistant, mock_hub
):
    """Changing options must tear the hub down and bring it back up cleanly."""
    start, stop = mock_hub
    entry = await setup_entry(hass)
    assert len(hass.states.async_entity_ids("number")) == 4

    new_options = {
        **TOPOLOGY,
        CONF_INPUTS: [
            *TOPOLOGY[CONF_INPUTS],
            {"id": "mic", "label": "Mic", "ch_l": 7, "default": 0.5},
        ],
    }
    hass.config_entries.async_update_entry(entry, options=new_options)
    await hass.async_block_till_done()

    # 2 faders + 2 inputs x 2 outputs
    assert len(hass.states.async_entity_ids("number")) == 6
    assert hass.states.get("number.midas_mic_space").state == "0.5"

    # The old hub was stopped before the new one started — this is what keeps
    # the local UDP port bindable and stops refresh timers stacking up.
    assert stop.await_count == 1
    assert start.await_count == 2


async def test_setting_a_value_sends_to_every_path(hass: HomeAssistant, mock_hub):
    """A stereo send drives both L and R; a fader drives its single path."""
    await setup_entry(hass)

    with patch("custom_components.midas_osc.hub.MidasOSCHub.send") as send:
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.midas_pc_space", "value": 0.4},
            blocking=True,
        )

    assert send.call_count == 2
    assert {call.args[0] for call in send.call_args_list} == {
        "/ch/15/mix/01/level",
        "/ch/16/mix/01/level",
    }
    assert {call.args[1] for call in send.call_args_list} == {0.4}
    assert hass.states.get("number.midas_pc_space").state == "0.4"


async def test_fader_sends_to_its_dca_path(hass: HomeAssistant, mock_hub):
    await setup_entry(hass)

    with patch("custom_components.midas_osc.hub.MidasOSCHub.send") as send:
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.midas_space", "value": 0.8},
            blocking=True,
        )

    send.assert_called_once_with("/dca/1/fader", 0.8)


async def test_v1_entry_migrates_to_empty_topology(hass: HomeAssistant, mock_hub):
    """A pre-topology entry must load, not get stuck on a missing migration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Midas",
        data=CONNECTION,
        unique_id="10.0.0.5:10024",
        version=1,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.state is ConfigEntryState.LOADED
    assert entry.options[CONF_OUTPUTS] == []
    assert entry.options[CONF_INPUTS] == []
    # Connection details are preserved so the user only re-adds the topology.
    assert entry.data == CONNECTION
    assert hass.states.async_entity_ids("number") == []


async def test_port_in_use_retries_instead_of_failing_hard(hass: HomeAssistant):
    """A busy local port is transient, so the entry should retry, not error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Midas",
        data=CONNECTION,
        options=TOPOLOGY,
        unique_id="10.0.0.5:10024",
        version=2,
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.midas_osc.hub.MidasOSCHub.start",
        side_effect=OSError("address already in use"),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_platform_failure_releases_the_port(hass: HomeAssistant):
    """A failed platform setup must not leave the UDP socket bound."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Midas",
        data=CONNECTION,
        options=TOPOLOGY,
        unique_id="10.0.0.5:10024",
        version=2,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.midas_osc.hub.MidasOSCHub.start",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.midas_osc.hub.MidasOSCHub.stop", new_callable=AsyncMock
        ) as stop,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            side_effect=RuntimeError("platform boom"),
        ),
    ):
        # HA traps the error itself and marks the entry as failed.
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    stop.assert_awaited_once()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
