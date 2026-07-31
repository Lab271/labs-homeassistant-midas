# labs-homeassistant-midas

Home Assistant custom integration for the **Midas M32** (and compatible Behringer X32) digital mixer over OSC. Exposes mixer faders and routing sends as Home Assistant `number` entities so you can control room volumes and channel routing from HA dashboards and automations.

**Status:** wip (`v0.1.0`) — the mixer topology is now defined in the UI, so the integration is no longer specific to one install.

## Concept

You describe your mixer in terms of **outputs** and **inputs**:

- An **output** is somewhere you mix towards — typically a room or zone. It has a **DCA** (its overall volume) and a **mix bus** (what sources are sent to).
- An **input** is a source you route. It has a left channel and, for stereo sources, a right channel. Mono sources use the left channel only.

From that, the integration generates:

- one fader entity per output — the room volume
- one send entity per **input × output** pair — how much of that source goes to that room

So 3 outputs and 2 inputs gives 3 faders + 6 sends = 9 entities. Stereo sends drive both L and R channels together from a single entity.

## What it does

- Runs an OSC client/server inside Home Assistant
- Subscribes to mixer state (`/xremote`) and re-polls every 8 seconds, so changes made on the physical desk show up in HA
- Exposes per-output DCA faders and per-route sends as `number` entities (range 0.0–1.0)

What it does **not** do (yet):

- Mute, EQ, scenes, or anything beyond fader levels
- Reordering or renaming inputs/outputs after creation (remove and re-add instead)

## Install (HACS)

1. Add this repo as a custom HACS repository: `Lab271/labs-homeassistant-midas`, category *Integration*.
2. Install **Midas OSC** from HACS.
3. Restart Home Assistant.
4. *Settings → Devices & Services → Add Integration → Midas OSC*.

## Install (manual)

```bash
git clone https://github.com/Lab271/labs-homeassistant-midas.git /tmp/midas
cp -r /tmp/midas/custom_components/midas_osc ~/.homeassistant/custom_components/
# restart Home Assistant
```

## Setup

The config flow walks you through three stages.

### 1. Connection

| Field | Default | Notes |
| --- | --- | --- |
| Name | `Midas` | Friendly name; prefixes every entity |
| Host | — | Mixer IP or hostname (required) |
| Port | `10023` | Mixer OSC port |
| Local port | `10024` | Local UDP port the integration binds to receive replies |

Each mixer needs its own local port — the host/local-port pair must be unique across entries.

### 2. Outputs

Added one at a time, ticking *Add another output* to continue.

| Field | Notes |
| --- | --- |
| Name | e.g. `Space` |
| DCA number | The DCA controlling this output's level (1–16) |
| Mix bus number | The bus sources are sent to (1–16). For stereo bus pairs, the odd-numbered bus |

### 3. Inputs

Added the same way.

| Field | Notes |
| --- | --- |
| Name | e.g. `PC` |
| Left channel | Input channel (1–32) |
| Right channel | Right channel of a stereo pair. **Leave empty for a mono source** |
| Default level | Starting level (0.0–1.0) until the mixer reports its real value |

### Example

The Lab271 setup — three rooms fed by a receiver and a PC:

| Output | DCA | Bus |
| --- | --- | --- |
| Space | 1 | 1 |
| Desks | 2 | 3 |
| Makerspace | 3 | 5 |

| Input | Left | Right |
| --- | --- | --- |
| Receiver | 9 | 10 |
| PC | 15 | 16 |

Produces 3 faders (`number.midas_space`, …) and 6 sends (`number.midas_pc_space`, …).

## Reconfiguring

*Settings → Devices & Services → Midas OSC → **Configure***:

- **Connection settings** — host, ports, name
- **Add an output** / **Add an input**
- **Remove outputs** / **Remove inputs** — removing an output also removes every send into it
- **Default output level** — the startup level for all output faders

Saving reloads the integration; entity IDs of everything you kept are preserved.

## Upgrading from v0.0.x

**v0.1.0 replaces the hardcoded topology and changes entity unique IDs.** Old entities do not carry over.

A v0.0.x entry is migrated automatically to keep its connection details, but loads with **no entities** — open *Configure* and add your outputs and inputs to recreate them. The stale entities from the old version can then be deleted from the entity registry, and any dashboards or automations referencing them need repointing at the new entity IDs.

## OSC paths

Generated from your topology, matching the M32/X32 scheme:

| Entity | Path |
| --- | --- |
| Output fader | `/dca/{dca}/fader` |
| Send | `/ch/{channel:02d}/mix/{bus:02d}/level` |

## Limitations

- **No auth.** OSC over UDP, no encryption — keep the mixer on a trusted network.
- **Assumed state.** Values are polled every 8 seconds; a change on the desk takes up to that long to appear in HA.
- Stereo sends assume L and R are kept at the same level.

## Development

Uses [uv](https://docs.astral.sh/uv/):

```bash
uv sync          # create the dev environment
uv run pytest    # run the test suite
```

`tests/test_topology.py` includes a regression test asserting the config-driven builder reproduces the exact OSC paths the pre-v0.1.0 hardcoded topology emitted.

## Dependencies

- `python-osc==1.9.0` (declared in [`manifest.json`](custom_components/midas_osc/manifest.json))

## Naming

The Midas M32C and any other audio device on the network follow the [Lab271 naming convention](https://github.com/Lab271/labs-infra-overview/blob/main/naming.md): the `aud` class with 2-digit zero-padded numbering, e.g. `sbplabaud01`.

## Owner

`@LAB271` — see [labs-infra-overview](https://github.com/Lab271/labs-infra-overview) for the full Lab271 infra index and conventions.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Please report vulnerabilities privately, not as a GitHub issue. See
[SECURITY.md](SECURITY.md).

## License

Copyright 2026 Schuberg Philis B.V.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
these files except in compliance with the License. You may obtain a copy of the
License in [LICENSE](LICENSE) or at <https://www.apache.org/licenses/LICENSE-2.0>.

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.
