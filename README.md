# labs-homeassistant-midas

Home Assistant custom integration for the **Midas M32** digital mixer over OSC. Exposes mixer faders and routing sends as Home Assistant `number` entities so you can control room volumes and channel routing from HA dashboards and automations.

**Status:** wip (`v0.0.3`) — works against the Lab271 mixer; entity topology is hardcoded, connection details are UI-configurable.

## Scope

This integration is built for the Lab271 audio setup, where one Midas M32 routes audio between three rooms (Space, Desks, Makerspace) and several stereo sources (AR desks, AR space, AR maker, PC). Each room is a DCA fader; each source-to-room route is a stereo send.

What this repo does:

- Runs an OSC client/server inside Home Assistant
- Subscribes to mixer state (`/xremote`) and re-polls every 8 seconds
- Exposes per-room DCA faders as `number` entities
- Exposes per-route stereo sends as paired `number` entities (L/R kept in sync)

What it does **not** do (yet):

- Generic, configurable channel/DCA mapping — the topology is hardcoded in [`number.py`](custom_components/midas_osc/number.py)
- Mute, EQ, scenes, or anything beyond fader levels

## Install (HACS)

1. Add this repo as a custom HACS repository: `Lab271/labs-homeassistant-midas`, category *Integration*.
2. Install **Midas OSC** from HACS.
3. Restart Home Assistant.
4. *Settings → Devices & Services → Add Integration → Midas OSC*. Fill in:
   - **Name** — friendly name shown in HA (default `Midas`)
   - **Host** — mixer IP or hostname
   - **Port** — mixer OSC port (default `10023`)
   - **Local port** — local UDP port the integration binds to receive replies (default `10024`)

## Install (manual)

```bash
git clone https://github.com/Lab271/labs-homeassistant-midas.git /tmp/midas
cp -r /tmp/midas/custom_components/midas_osc ~/.homeassistant/custom_components/
# restart Home Assistant
```

## Configuration

UI-only via the config flow. Fields:

| Field | Default | Notes |
| --- | --- | --- |
| Name | `Midas` | Friendly name shown in HA |
| Host | — | Mixer IP or hostname (required) |
| Port | `10023` | Mixer OSC port |
| Local port | `10024` | Local UDP port the integration binds to receive replies |

To change these after setup, delete the integration entry and add it again.

## Limitations

- **Channel/DCA mapping is hardcoded.** The list of rooms and sends in `async_setup_entry` matches the Lab271 routing scheme; adapt the entity list in [`number.py`](custom_components/midas_osc/number.py) for your own setup.
- **No auth.** OSC over UDP, no encryption — keep the mixer on a trusted network.

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
