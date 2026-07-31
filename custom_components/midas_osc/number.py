"""Number entities for the configured Midas topology."""

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .hub import MidasOSCHub
from .topology import EntitySpec, build_entity_specs


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up Midas OSC number entities from the configured topology."""
    hub: MidasOSCHub = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        MidasLevelEntity(entry, spec, hub)
        for spec in build_entity_specs(dict(entry.options))
    )


class MidasLevelEntity(NumberEntity):
    """A 0.0-1.0 level driving one or more OSC paths in lockstep.

    Covers all three cases: a DCA fader (one path), a mono send (one path) and
    a stereo send (L and R, always set to the same value).
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1.0
    _attr_native_step = 0.05

    def __init__(self, entry: ConfigEntry, spec: EntitySpec, hub: MidasOSCHub):
        self._spec = spec
        self._hub = hub
        self._value = spec.default
        self._attr_name = spec.label
        self._attr_unique_id = f"{entry.entry_id}_{spec.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Midas",
            model="M32",
        )

    @property
    def native_value(self):
        return self._value

    async def async_added_to_hass(self) -> None:
        """Start receiving mixer updates for this entity's primary path."""
        self._hub.register(self._spec.primary_path, self)

    async def async_will_remove_from_hass(self) -> None:
        """Stop the hub polling and routing a path with no entity behind it."""
        self._hub.unregister(self._spec.primary_path)

    def update_value(self, value: float) -> None:
        """Apply a value pushed from the mixer."""
        self._value = round(value, 2)
        if self.hass is not None:
            self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        self._value = round(value, 2)
        for path in self._spec.paths:
            self._hub.send(path, self._value)
        self.async_write_ha_state()
