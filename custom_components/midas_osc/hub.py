"""Shared OSC transport for a single Midas mixer."""

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_server import AsyncIOOSCUDPServer

from .const import REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)


class MidasOSCHub:
    """Shared OSC server — sends queries and receives updates from the mixer."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, local_port: int):
        self._hass = hass
        self._host = host
        self._port = port
        self._local_port = local_port
        self._entities: dict[str, object] = {}
        self._transport = None
        self._unsub_refresh = None
        self._dispatcher = Dispatcher()
        self._dispatcher.set_default_handler(self._handle_message)

    def register(self, path: str, entity) -> None:
        """Route updates for an OSC path to an entity."""
        self._entities[path] = entity

    def unregister(self, path: str) -> None:
        """Stop routing updates for an OSC path, and stop polling it."""
        self._entities.pop(path, None)

    def _handle_message(self, address, *args):
        entity = self._entities.get(address)
        if entity is not None and args:
            entity.update_value(float(args[0]))

    def send(self, path: str, *args) -> None:
        """Send an OSC message to the mixer. No-op before start()/after stop()."""
        if self._transport is None:
            return
        builder = OscMessageBuilder(address=path)
        for arg in args:
            builder.add_arg(arg)
        self._transport.sendto(builder.build().dgram, (self._host, self._port))

    async def start(self) -> None:
        """Bind the local UDP port and begin subscribing to mixer state."""
        loop = asyncio.get_running_loop()
        server = AsyncIOOSCUDPServer(
            ("0.0.0.0", self._local_port), self._dispatcher, loop
        )
        self._transport, _ = await server.create_serve_endpoint()

        # Subscribe and query all current values immediately
        self._refresh()

        # Keep the subscription alive and re-poll every REFRESH_INTERVAL
        self._unsub_refresh = async_track_time_interval(
            self._hass, lambda _: self._refresh(), REFRESH_INTERVAL
        )

    async def stop(self) -> None:
        """Cancel the refresh timer and release the local UDP port."""
        if self._unsub_refresh is not None:
            self._unsub_refresh()
            self._unsub_refresh = None
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._entities.clear()

    def _refresh(self) -> None:
        self.send("/xremote")
        for path in list(self._entities):
            self.send(path)
