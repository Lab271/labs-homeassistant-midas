"""Tests for the OSC hub's registration, polling and teardown."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.midas_osc.hub import MidasOSCHub


@pytest.fixture
async def hub(hass: HomeAssistant) -> MidasOSCHub:
    """A hub that is always torn down, so a leaked timer fails the test."""
    instance = MidasOSCHub(hass, host="10.0.0.5", port=10023, local_port=10024)
    yield instance
    await instance.stop()


class FakeEntity:
    def __init__(self):
        self.values = []

    def update_value(self, value):
        self.values.append(value)


async def started(hub: MidasOSCHub):
    """Start the hub with a fake UDP endpoint."""
    transport = MagicMock()
    with patch("custom_components.midas_osc.hub.AsyncIOOSCUDPServer") as server:
        server.return_value.create_serve_endpoint = _endpoint(transport)
        await hub.start()
    return transport


def _endpoint(transport):
    async def create_serve_endpoint():
        return transport, MagicMock()

    return create_serve_endpoint


async def test_send_is_a_noop_before_start(hub: MidasOSCHub):
    """No transport yet — sending must not raise."""
    hub.send("/dca/1/fader", 0.5)


async def test_send_addresses_the_mixer(hub: MidasOSCHub):
    transport = await started(hub)
    transport.reset_mock()

    hub.send("/dca/1/fader", 0.5)

    transport.sendto.assert_called_once()
    dgram, addr = transport.sendto.call_args.args
    assert addr == ("10.0.0.5", 10023)
    assert b"/dca/1/fader" in dgram


async def test_incoming_message_reaches_the_registered_entity(hub: MidasOSCHub):
    entity = FakeEntity()
    hub.register("/dca/1/fader", entity)

    hub._handle_message("/dca/1/fader", 0.42)

    assert entity.values == [0.42]


async def test_message_for_unknown_path_is_ignored(hub: MidasOSCHub):
    entity = FakeEntity()
    hub.register("/dca/1/fader", entity)

    hub._handle_message("/dca/9/fader", 0.42)
    hub._handle_message("/dca/1/fader")  # no args

    assert entity.values == []


async def test_unregister_stops_updates_and_polling(hub: MidasOSCHub):
    entity = FakeEntity()
    hub.register("/dca/1/fader", entity)
    hub.unregister("/dca/1/fader")

    hub._handle_message("/dca/1/fader", 0.42)
    assert entity.values == []

    transport = await started(hub)
    transport.reset_mock()
    hub._refresh()
    # Only /xremote, no query for the unregistered path.
    assert transport.sendto.call_count == 1


async def test_unregister_is_idempotent(hub: MidasOSCHub):
    hub.unregister("/never/registered")


async def test_refresh_subscribes_then_queries_every_path(hub: MidasOSCHub):
    hub.register("/dca/1/fader", FakeEntity())
    hub.register("/dca/2/fader", FakeEntity())

    transport = await started(hub)
    transport.reset_mock()
    hub._refresh()

    sent = [call.args[0] for call in transport.sendto.call_args_list]
    assert len(sent) == 3
    assert b"/xremote" in sent[0]
    assert b"/dca/1/fader" in sent[1]
    assert b"/dca/2/fader" in sent[2]


async def test_start_polls_immediately(hub: MidasOSCHub):
    """State is fetched at startup, not only after the first interval."""
    hub.register("/dca/1/fader", FakeEntity())
    transport = await started(hub)

    sent = [call.args[0] for call in transport.sendto.call_args_list]
    assert any(b"/xremote" in dgram for dgram in sent)
    assert any(b"/dca/1/fader" in dgram for dgram in sent)


async def test_stop_releases_the_port_and_cancels_the_timer(hub: MidasOSCHub):
    transport = await started(hub)
    assert hub._unsub_refresh is not None

    await hub.stop()

    transport.close.assert_called_once()
    assert hub._unsub_refresh is None
    assert hub._transport is None


async def test_stop_then_send_is_a_noop(hub: MidasOSCHub):
    """After teardown the hub must not touch the closed transport."""
    transport = await started(hub)
    await hub.stop()
    transport.reset_mock()

    hub.send("/dca/1/fader", 0.5)

    transport.sendto.assert_not_called()


async def test_refresh_timer_stops_firing_after_stop(hub: MidasOSCHub):
    """The leak that would stack timers across reloads."""
    from datetime import timedelta

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    hub.register("/dca/1/fader", FakeEntity())
    transport = await started(hub)
    await hub.stop()
    transport.reset_mock()

    async_fire_time_changed(hub._hass, dt_util.utcnow() + timedelta(seconds=30))
    await hub._hass.async_block_till_done()

    transport.sendto.assert_not_called()
