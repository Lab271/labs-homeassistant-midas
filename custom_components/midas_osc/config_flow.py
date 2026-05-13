import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT

from .const import (
    DOMAIN,
    CONF_LOCAL_PORT,
    DEFAULT_MIXER_PORT,
    DEFAULT_LOCAL_PORT,
)


class MidasOSCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Midas OSC Controller."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default="Midas"): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_MIXER_PORT): int,
                vol.Required(CONF_LOCAL_PORT, default=DEFAULT_LOCAL_PORT): int,
            }),
        )
