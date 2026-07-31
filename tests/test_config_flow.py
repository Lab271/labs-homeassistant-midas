"""Tests for the multi-step config flow and the options flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.midas_osc.const import (
    CONF_ADD_ANOTHER,
    CONF_BUS,
    CONF_CH_L,
    CONF_CH_R,
    CONF_DCA,
    CONF_DEFAULT,
    CONF_INPUTS,
    CONF_LABEL,
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


@pytest.fixture(autouse=True)
def _no_real_socket():
    """Never bind a real UDP port during tests."""
    with (
        patch("custom_components.midas_osc.hub.MidasOSCHub.start"),
        patch("custom_components.midas_osc.hub.MidasOSCHub.stop"),
    ):
        yield


def output(label, dca, bus, add_another=False):
    return {
        CONF_LABEL: label,
        CONF_DCA: dca,
        CONF_BUS: bus,
        CONF_ADD_ANOTHER: add_another,
    }


def source(label, ch_l, ch_r=None, default=0.75, add_another=False):
    data = {
        CONF_LABEL: label,
        CONF_CH_L: ch_l,
        CONF_DEFAULT: default,
        CONF_ADD_ANOTHER: add_another,
    }
    if ch_r is not None:
        data[CONF_CH_R] = ch_r
    return data


async def start_flow(hass: HomeAssistant):
    """Begin the flow and submit the connection step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)


async def test_full_flow_builds_topology(hass: HomeAssistant):
    """Walk the whole flow: connection, two outputs, one stereo input."""
    result = await start_flow(hass)
    assert result["step_id"] == "output"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], output("Space", 1, 1, add_another=True)
    )
    assert result["step_id"] == "output"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], output("Desks", 2, 3)
    )
    assert result["step_id"] == "input"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], source("PC", 15, 16)
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Midas"
    assert result["data"] == CONNECTION

    options = result["options"]
    assert options[CONF_OUTPUTS] == [
        {"id": "space", "label": "Space", "dca": 1, "bus": 1},
        {"id": "desks", "label": "Desks", "dca": 2, "bus": 3},
    ]
    assert options[CONF_INPUTS] == [
        {"id": "pc", "label": "PC", "ch_l": 15, "ch_r": 16, "default": 0.75}
    ]
    assert CONF_OUTPUT_DEFAULT in options


async def test_mono_input_omits_right_channel(hass: HomeAssistant):
    result = await start_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], output("Space", 1, 1)
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], source("Mic", 7)
    )
    assert result["options"][CONF_INPUTS] == [
        {"id": "mic", "label": "Mic", "ch_l": 7, "default": 0.75}
    ]


async def test_duplicate_output_label_is_rejected(hass: HomeAssistant):
    result = await start_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], output("Space", 1, 1, add_another=True)
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], output("space", 2, 3)
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {CONF_LABEL: "duplicate_label"}


async def test_blank_output_label_is_rejected(hass: HomeAssistant):
    result = await start_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], output("   ", 1, 1)
    )
    assert result["errors"] == {CONF_LABEL: "empty_label"}


async def test_duplicate_host_and_local_port_aborts(hass: HomeAssistant):
    MockConfigEntry(
        domain=DOMAIN,
        data=CONNECTION,
        unique_id=f"{CONNECTION['host']}:{CONNECTION[CONF_LOCAL_PORT]}",
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CONNECTION
    )
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_out_of_range_dca_is_rejected(hass: HomeAssistant):
    """Voluptuous range validation rejects a DCA above the mixer's 16."""
    result = await start_flow(hass)
    with pytest.raises(data_entry_flow.InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], output("Space", 99, 1)
        )


# -- options flow --------------------------------------------------------


def configured_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Midas",
        data=CONNECTION,
        unique_id=f"{CONNECTION['host']}:{CONNECTION[CONF_LOCAL_PORT]}",
        options={
            CONF_OUTPUTS: [
                {"id": "space", "label": "Space", "dca": 1, "bus": 1},
                {"id": "desks", "label": "Desks", "dca": 2, "bus": 3},
            ],
            CONF_INPUTS: [
                {"id": "pc", "label": "PC", "ch_l": 15, "ch_r": 16, "default": 0.75}
            ],
            CONF_OUTPUT_DEFAULT: 0.35,
        },
    )
    entry.add_to_hass(hass)
    return entry


async def open_options(hass: HomeAssistant, entry, step: str):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": step}
    )


async def test_options_add_input(hass: HomeAssistant):
    entry = configured_entry(hass)
    result = await open_options(hass, entry, "add_input")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_LABEL: "Receiver", CONF_CH_L: 9, CONF_CH_R: 10, CONF_DEFAULT: 0.5},
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_INPUTS][-1] == {
        "id": "receiver",
        "label": "Receiver",
        "ch_l": 9,
        "ch_r": 10,
        "default": 0.5,
    }


async def test_options_add_output(hass: HomeAssistant):
    entry = configured_entry(hass)
    result = await open_options(hass, entry, "add_output")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_LABEL: "Makerspace", CONF_DCA: 3, CONF_BUS: 5}
    )
    assert result["data"][CONF_OUTPUTS][-1] == {
        "id": "makerspace",
        "label": "Makerspace",
        "dca": 3,
        "bus": 5,
    }


async def test_options_remove_output(hass: HomeAssistant):
    entry = configured_entry(hass)
    result = await open_options(hass, entry, "remove_output")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_OUTPUTS: ["space"]}
    )
    remaining = [o["id"] for o in result["data"][CONF_OUTPUTS]]
    assert remaining == ["desks"]
    # Inputs are untouched by an output removal.
    assert [i["id"] for i in result["data"][CONF_INPUTS]] == ["pc"]


async def test_options_remove_nothing_keeps_everything(hass: HomeAssistant):
    entry = configured_entry(hass)
    result = await open_options(hass, entry, "remove_input")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_INPUTS: []}
    )
    assert [i["id"] for i in result["data"][CONF_INPUTS]] == ["pc"]


async def test_options_duplicate_label_rejected(hass: HomeAssistant):
    entry = configured_entry(hass)
    result = await open_options(hass, entry, "add_output")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_LABEL: "Space", CONF_DCA: 4, CONF_BUS: 7}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {CONF_LABEL: "duplicate_label"}


async def test_options_connection_updates_entry_data(hass: HomeAssistant):
    entry = configured_entry(hass)
    result = await open_options(hass, entry, "connection")
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {**CONNECTION, "host": "10.0.0.9", "name": "Studio"},
    )
    await hass.async_block_till_done()
    assert entry.data["host"] == "10.0.0.9"
    assert entry.title == "Studio"
    # Topology survives a connection-only edit.
    assert [o["id"] for o in entry.options[CONF_OUTPUTS]] == ["space", "desks"]


async def test_options_levels(hass: HomeAssistant):
    entry = configured_entry(hass)
    result = await open_options(hass, entry, "levels")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_OUTPUT_DEFAULT: 0.6}
    )
    assert result["data"][CONF_OUTPUT_DEFAULT] == 0.6
