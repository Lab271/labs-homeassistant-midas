# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Schuberg Philis / Lab271
import asyncio
from datetime import timedelta

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.osc_message_builder import OscMessageBuilder

from .const import DOMAIN, CONF_LOCAL_PORT

# EDIT BEFORE USE: the entity topology in async_setup_entry() below is
# hardcoded for the Lab271 install (room/source names, channel numbers,
# DCA assignments). Connection details (host/port/local port) come from
# the config entry — set them in the UI when adding the integration.


class MidasOSCHub:
    """Shared OSC server — sends queries and receives updates from the mixer."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, local_port: int):
        self._hass = hass
        self._host = host
        self._port = port
        self._local_port = local_port
        self._entities: dict[str, "MidasBaseEntity"] = {}
        self._transport = None
        self._dispatcher = Dispatcher()
        self._dispatcher.set_default_handler(self._handle_message)

    def register(self, path: str, entity: "MidasBaseEntity"):
        self._entities[path] = entity

    def _handle_message(self, address, *args):
        if address in self._entities and args:
            self._entities[address].update_value(float(args[0]))

    def _send(self, path: str, *args):
        if self._transport is None:
            return
        builder = OscMessageBuilder(address=path)
        for arg in args:
            builder.add_arg(arg)
        self._transport.sendto(builder.build().dgram, (self._host, self._port))

    async def start(self):
        loop = asyncio.get_running_loop()
        server = AsyncIOOSCUDPServer(("0.0.0.0", self._local_port), self._dispatcher, loop)
        self._transport, _ = await server.create_serve_endpoint()

        # Subscribe and query all current values immediately
        self._refresh()

        # Keep subscription alive and re-poll every 8 seconds
        async_track_time_interval(
            self._hass, lambda _: self._refresh(), timedelta(seconds=8)
        )

    def _refresh(self):
        self._send("/xremote")
        for path in self._entities:
            self._send(path)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Midas OSC number entities."""
    name = entry.data["name"]
    hub = MidasOSCHub(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        local_port=entry.data[CONF_LOCAL_PORT],
    )

    entities = [
        # Room volumes (DCA)
        MidasFaderEntity(f"{name} Space",      "/dca/1/fader", name, hub, default=0.35),
        MidasFaderEntity(f"{name} Desks",      "/dca/2/fader", name, hub, default=0.35),
        MidasFaderEntity(f"{name} Makerspace", "/dca/3/fader", name, hub, default=0.35),

        # AR Desks routing
        MidasStereoSendEntity(f"{name} AR Desks → Space",      "/ch/09/mix/01/level", "/ch/10/mix/01/level", name, hub, default=0.75),
        MidasStereoSendEntity(f"{name} AR Desks → Desks",      "/ch/09/mix/03/level", "/ch/10/mix/03/level", name, hub, default=0.75),
        MidasStereoSendEntity(f"{name} AR Desks → Makerspace", "/ch/09/mix/05/level", "/ch/10/mix/05/level", name, hub, default=0.75),

        # AR Space routing
        MidasStereoSendEntity(f"{name} AR Space → Space",      "/ch/11/mix/01/level", "/ch/12/mix/01/level", name, hub, default=0.75),
        MidasStereoSendEntity(f"{name} AR Space → Desks",      "/ch/11/mix/03/level", "/ch/12/mix/03/level", name, hub, default=0.0),
        MidasStereoSendEntity(f"{name} AR Space → Makerspace", "/ch/11/mix/05/level", "/ch/12/mix/05/level", name, hub, default=0.0),

        # AR Maker routing
        MidasStereoSendEntity(f"{name} AR Maker → Space",      "/ch/13/mix/01/level", "/ch/14/mix/01/level", name, hub, default=0.0),
        MidasStereoSendEntity(f"{name} AR Maker → Desks",      "/ch/13/mix/03/level", "/ch/14/mix/03/level", name, hub, default=0.0),
        MidasStereoSendEntity(f"{name} AR Maker → Makerspace", "/ch/13/mix/05/level", "/ch/14/mix/05/level", name, hub, default=0.75),

        # PC routing
        MidasStereoSendEntity(f"{name} PC → Space",      "/ch/15/mix/01/level", "/ch/16/mix/01/level", name, hub, default=0.75),
        MidasStereoSendEntity(f"{name} PC → Desks",      "/ch/15/mix/03/level", "/ch/16/mix/03/level", name, hub, default=0.75),
        MidasStereoSendEntity(f"{name} PC → Makerspace", "/ch/15/mix/05/level", "/ch/16/mix/05/level", name, hub, default=0.75),
    ]

    for entity in entities:
        entity.register_with_hub()

    async_add_entities(entities)
    await hub.start()


class MidasBaseEntity(NumberEntity):
    """Base class for Midas fader entities."""

    should_poll = False

    def __init__(self, name, device_info, hub: MidasOSCHub, default: float):
        self._attr_name = name
        self._attr_unique_id = name
        self._attr_device_info = device_info
        self._hub = hub
        self._value = default

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_device_info)},
            name=self._attr_device_info,
            manufacturer="Midas",
            model="M32",
            sw_version="1.0",
        )

    @property
    def native_value(self):
        return self._value

    @property
    def native_min_value(self):
        return 0.0

    @property
    def native_max_value(self):
        return 1.0

    @property
    def native_step(self):
        return 0.05

    def update_value(self, value: float):
        self._value = round(value, 2)
        self.async_write_ha_state()

    def register_with_hub(self):
        raise NotImplementedError


class MidasFaderEntity(MidasBaseEntity):
    """A single OSC fader (DCA room volume)."""

    def __init__(self, name, osc_path, device_info, hub, default=0.75):
        super().__init__(name, device_info, hub, default)
        self._osc_path = osc_path

    def register_with_hub(self):
        self._hub.register(self._osc_path, self)

    async def async_set_native_value(self, value):
        self._value = round(value, 2)
        self._hub._send(self._osc_path, self._value)
        self.async_write_ha_state()


class MidasStereoSendEntity(MidasBaseEntity):
    """A stereo channel send — controls L and R OSC paths together."""

    def __init__(self, name, osc_path_l, osc_path_r, device_info, hub, default=0.75):
        super().__init__(name, device_info, hub, default)
        self._osc_path_l = osc_path_l
        self._osc_path_r = osc_path_r

    def register_with_hub(self):
        # Register on L path — L and R are always identical so we only need one
        self._hub.register(self._osc_path_l, self)

    async def async_set_native_value(self, value):
        self._value = round(value, 2)
        self._hub._send(self._osc_path_l, self._value)
        self._hub._send(self._osc_path_r, self._value)
        self.async_write_ha_state()
