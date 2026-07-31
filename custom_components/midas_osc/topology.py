# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Schuberg Philis / Lab271
"""Turn the user-configured topology into a flat list of entity descriptions.

Pure functions only — no Home Assistant imports beyond ``slugify`` — so this can
be unit-tested without spinning up HA.
"""

from dataclasses import dataclass

from homeassistant.util import slugify

from .const import (
    CONF_BUS,
    CONF_CH_L,
    CONF_CH_R,
    CONF_DCA,
    CONF_DEFAULT,
    CONF_ID,
    CONF_INPUTS,
    CONF_LABEL,
    CONF_OUTPUT_DEFAULT,
    CONF_OUTPUTS,
    DEFAULT_FADER_LEVEL,
    DEFAULT_SEND_LEVEL,
    FADER_PATH,
    SEND_PATH,
)


@dataclass(frozen=True)
class EntitySpec:
    """One number entity: a label, a stable key, and the OSC paths it drives."""

    key: str
    label: str
    paths: tuple[str, ...]
    default: float

    @property
    def primary_path(self) -> str:
        """The path we subscribe to for state. L and R always track together."""
        return self.paths[0]


def make_id(label: str, existing: list[dict]) -> str:
    """Slugify ``label`` into an id unique among ``existing`` entries.

    The id is generated once, when the input/output is created, and never
    changes afterwards — entity unique_ids are built from it, so relabelling
    must not disturb it.
    """
    # slugify() already yields "unknown" for labels with no usable characters.
    base = slugify(label)
    taken = {item.get(CONF_ID) for item in existing}
    if base not in taken:
        return base
    suffix = 2
    while f"{base}_{suffix}" in taken:
        suffix += 1
    return f"{base}_{suffix}"


def _send_paths(source: dict, output: dict) -> tuple[str, ...]:
    """OSC paths for one source into one output — one path if mono, two if stereo."""
    bus = output[CONF_BUS]
    channels = [source[CONF_CH_L]]
    ch_r = source.get(CONF_CH_R)
    if ch_r:
        channels.append(ch_r)
    return tuple(SEND_PATH.format(ch=ch, bus=bus) for ch in channels)


def build_entity_specs(options: dict) -> list[EntitySpec]:
    """Build every entity implied by the configured topology.

    One DCA fader per output, plus one send per (input x output) pair.
    """
    outputs = options.get(CONF_OUTPUTS) or []
    inputs = options.get(CONF_INPUTS) or []
    fader_default = options.get(CONF_OUTPUT_DEFAULT, DEFAULT_FADER_LEVEL)

    specs: list[EntitySpec] = []

    for output in outputs:
        specs.append(
            EntitySpec(
                key=f"fader_{output[CONF_ID]}",
                label=output[CONF_LABEL],
                paths=(FADER_PATH.format(dca=output[CONF_DCA]),),
                default=fader_default,
            )
        )

    for source in inputs:
        for output in outputs:
            specs.append(
                EntitySpec(
                    key=f"send_{source[CONF_ID]}_{output[CONF_ID]}",
                    label=f"{source[CONF_LABEL]} → {output[CONF_LABEL]}",
                    paths=_send_paths(source, output),
                    default=source.get(CONF_DEFAULT, DEFAULT_SEND_LEVEL),
                )
            )

    return specs
