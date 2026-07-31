"""Config and options flows for Midas OSC."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ADD_ANOTHER,
    CONF_BUS,
    CONF_CH_L,
    CONF_CH_R,
    CONF_DCA,
    CONF_DEFAULT,
    CONF_ID,
    CONF_INPUTS,
    CONF_LABEL,
    CONF_LOCAL_PORT,
    CONF_OUTPUT_DEFAULT,
    CONF_OUTPUTS,
    DEFAULT_FADER_LEVEL,
    DEFAULT_LOCAL_PORT,
    DEFAULT_MIXER_PORT,
    DEFAULT_SEND_LEVEL,
    DOMAIN,
    MAX_BUS,
    MAX_CHANNEL,
    MAX_DCA,
)
from .topology import make_id

LEVEL = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0))


def connection_schema(defaults: dict | None = None) -> vol.Schema:
    """Schema for the mixer connection details."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Midas")): str,
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_MIXER_PORT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(
                CONF_LOCAL_PORT,
                default=defaults.get(CONF_LOCAL_PORT, DEFAULT_LOCAL_PORT),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        }
    )


def output_schema(add_another: bool = True) -> vol.Schema:
    """Schema for one output (a room / destination: a DCA plus a mix bus)."""
    fields = {
        vol.Required(CONF_LABEL): str,
        vol.Required(CONF_DCA, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_DCA)
        ),
        vol.Required(CONF_BUS, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_BUS)
        ),
    }
    if add_another:
        fields[vol.Optional(CONF_ADD_ANOTHER, default=False)] = bool
    return vol.Schema(fields)


def input_schema(add_another: bool = True) -> vol.Schema:
    """Schema for one input (a source: one channel, or an L/R pair)."""
    fields = {
        vol.Required(CONF_LABEL): str,
        vol.Required(CONF_CH_L, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_CHANNEL)
        ),
        # Leave the right channel empty for a mono source.
        vol.Optional(CONF_CH_R): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_CHANNEL)
        ),
        vol.Required(CONF_DEFAULT, default=DEFAULT_SEND_LEVEL): LEVEL,
    }
    if add_another:
        fields[vol.Optional(CONF_ADD_ANOTHER, default=False)] = bool
    return vol.Schema(fields)


def _picker(items: list[dict]) -> SelectSelector:
    """A multi-select of existing inputs/outputs, by id but showing labels."""
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=item[CONF_ID], label=item[CONF_LABEL])
                for item in items
            ],
            multiple=True,
            mode=SelectSelectorMode.LIST,
        )
    )


def _duplicate_label(label: str, existing: list[dict]) -> bool:
    return any(
        item[CONF_LABEL].strip().casefold() == label.strip().casefold()
        for item in existing
    )


def _make_output(user_input: dict, existing: list[dict]) -> dict:
    label = user_input[CONF_LABEL].strip()
    return {
        CONF_ID: make_id(label, existing),
        CONF_LABEL: label,
        CONF_DCA: user_input[CONF_DCA],
        CONF_BUS: user_input[CONF_BUS],
    }


def _make_input(user_input: dict, existing: list[dict]) -> dict:
    label = user_input[CONF_LABEL].strip()
    entry = {
        CONF_ID: make_id(label, existing),
        CONF_LABEL: label,
        CONF_CH_L: user_input[CONF_CH_L],
        CONF_DEFAULT: user_input[CONF_DEFAULT],
    }
    if user_input.get(CONF_CH_R):
        entry[CONF_CH_R] = user_input[CONF_CH_R]
    return entry


class MidasOSCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Midas OSC Controller."""

    VERSION = 2

    def __init__(self) -> None:
        self._connection: dict[str, Any] = {}
        self._outputs: list[dict] = []
        self._inputs: list[dict] = []

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return MidasOSCOptionsFlow()

    async def async_step_user(self, user_input=None):
        """Collect the mixer connection details."""
        if user_input is not None:
            # Two entries cannot bind the same local UDP port.
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_LOCAL_PORT]}"
            )
            self._abort_if_unique_id_configured()
            self._connection = dict(user_input)
            return await self.async_step_output()

        return self.async_show_form(step_id="user", data_schema=connection_schema())

    async def async_step_output(self, user_input=None):
        """Add an output, looping until the user stops."""
        errors: dict[str, str] = {}

        if user_input is not None:
            label = user_input[CONF_LABEL].strip()
            if not label:
                errors[CONF_LABEL] = "empty_label"
            elif _duplicate_label(label, self._outputs):
                errors[CONF_LABEL] = "duplicate_label"
            else:
                self._outputs.append(_make_output(user_input, self._outputs))
                if user_input.get(CONF_ADD_ANOTHER):
                    return await self.async_step_output()
                return await self.async_step_input()

        return self.async_show_form(
            step_id="output",
            data_schema=output_schema(),
            errors=errors,
            description_placeholders={"count": str(len(self._outputs))},
        )

    async def async_step_input(self, user_input=None):
        """Add an input, looping until the user stops, then create the entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            label = user_input[CONF_LABEL].strip()
            if not label:
                errors[CONF_LABEL] = "empty_label"
            elif _duplicate_label(label, self._inputs):
                errors[CONF_LABEL] = "duplicate_label"
            else:
                self._inputs.append(_make_input(user_input, self._inputs))
                if user_input.get(CONF_ADD_ANOTHER):
                    return await self.async_step_input()
                return self._create_entry()

        return self.async_show_form(
            step_id="input",
            data_schema=input_schema(),
            errors=errors,
            description_placeholders={"count": str(len(self._inputs))},
        )

    def _create_entry(self):
        return self.async_create_entry(
            title=self._connection[CONF_NAME],
            data=self._connection,
            options={
                CONF_OUTPUTS: self._outputs,
                CONF_INPUTS: self._inputs,
                CONF_OUTPUT_DEFAULT: DEFAULT_FADER_LEVEL,
            },
        )


class MidasOSCOptionsFlow(config_entries.OptionsFlow):
    """Edit the connection details and the topology after setup."""

    async def async_step_init(self, user_input=None):
        """Show the top-level menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "connection",
                "add_output",
                "add_input",
                "remove_output",
                "remove_input",
                "levels",
            ],
        )

    # -- helpers ---------------------------------------------------------

    @property
    def _outputs(self) -> list[dict]:
        return list(self.config_entry.options.get(CONF_OUTPUTS) or [])

    @property
    def _inputs(self) -> list[dict]:
        return list(self.config_entry.options.get(CONF_INPUTS) or [])

    def _save(self, *, outputs=None, inputs=None, output_default=None):
        """Write topology back to entry.options, which reloads the entry."""
        options = dict(self.config_entry.options)
        if outputs is not None:
            options[CONF_OUTPUTS] = outputs
        if inputs is not None:
            options[CONF_INPUTS] = inputs
        if output_default is not None:
            options[CONF_OUTPUT_DEFAULT] = output_default
        return self.async_create_entry(title="", data=options)

    # -- steps -----------------------------------------------------------

    async def async_step_connection(self, user_input=None):
        """Edit host/port/local port. These live in entry.data, not options."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=user_input[CONF_NAME],
                data={**self.config_entry.data, **user_input},
            )
            # async_update_entry already schedules a reload via the update
            # listener; return an unchanged options payload.
            return self.async_create_entry(
                title="", data=dict(self.config_entry.options)
            )

        return self.async_show_form(
            step_id="connection",
            data_schema=connection_schema(dict(self.config_entry.data)),
        )

    async def async_step_add_output(self, user_input=None):
        errors: dict[str, str] = {}
        outputs = self._outputs

        if user_input is not None:
            label = user_input[CONF_LABEL].strip()
            if not label:
                errors[CONF_LABEL] = "empty_label"
            elif _duplicate_label(label, outputs):
                errors[CONF_LABEL] = "duplicate_label"
            else:
                outputs.append(_make_output(user_input, outputs))
                return self._save(outputs=outputs)

        return self.async_show_form(
            step_id="add_output",
            data_schema=output_schema(add_another=False),
            errors=errors,
        )

    async def async_step_add_input(self, user_input=None):
        errors: dict[str, str] = {}
        inputs = self._inputs

        if user_input is not None:
            label = user_input[CONF_LABEL].strip()
            if not label:
                errors[CONF_LABEL] = "empty_label"
            elif _duplicate_label(label, inputs):
                errors[CONF_LABEL] = "duplicate_label"
            else:
                inputs.append(_make_input(user_input, inputs))
                return self._save(inputs=inputs)

        return self.async_show_form(
            step_id="add_input",
            data_schema=input_schema(add_another=False),
            errors=errors,
        )

    async def async_step_remove_output(self, user_input=None):
        outputs = self._outputs
        if not outputs:
            return self.async_abort(reason="nothing_to_remove")

        if user_input is not None:
            drop = set(user_input.get(CONF_OUTPUTS) or [])
            return self._save(outputs=[o for o in outputs if o[CONF_ID] not in drop])

        return self.async_show_form(
            step_id="remove_output",
            data_schema=vol.Schema(
                {vol.Optional(CONF_OUTPUTS, default=[]): _picker(outputs)}
            ),
        )

    async def async_step_remove_input(self, user_input=None):
        inputs = self._inputs
        if not inputs:
            return self.async_abort(reason="nothing_to_remove")

        if user_input is not None:
            drop = set(user_input.get(CONF_INPUTS) or [])
            return self._save(inputs=[i for i in inputs if i[CONF_ID] not in drop])

        return self.async_show_form(
            step_id="remove_input",
            data_schema=vol.Schema(
                {vol.Optional(CONF_INPUTS, default=[]): _picker(inputs)}
            ),
        )

    async def async_step_levels(self, user_input=None):
        """Change the startup level applied to every output fader."""
        if user_input is not None:
            return self._save(output_default=user_input[CONF_OUTPUT_DEFAULT])

        current = self.config_entry.options.get(
            CONF_OUTPUT_DEFAULT, DEFAULT_FADER_LEVEL
        )
        return self.async_show_form(
            step_id="levels",
            data_schema=vol.Schema(
                {vol.Required(CONF_OUTPUT_DEFAULT, default=current): LEVEL}
            ),
        )
