# labs-homeassistant-midas

Home Assistant custom integration for the **Midas M32** digital mixer over OSC. Exposes mixer faders and routing sends as Home Assistant `number` entities so you can control room volumes and channel routing from HA dashboards and automations.

**Status:** wip (`v0.0.2`) — works against the Lab271 mixer; topology is currently hardcoded.

## Scope

This integration is built for the Lab271 audio setup, where one Midas M32 routes audio between three rooms (Space, Desks, Makerspace) and several stereo sources (AR desks, AR space, AR maker, PC). Each room is a DCA fader; each source-to-room route is a stereo send.

What this repo does:

- Runs an OSC client/server inside Home Assistant
- Subscribes to mixer state (`/xremote`) and re-polls every 8 seconds
- Exposes per-room DCA faders as `number` entities
- Exposes per-route stereo sends as paired `number` entities (L/R kept in sync)

What it does **not** do (yet):

- Generic, configurable channel/DCA mapping — the topology is hardcoded in [`number.py`](number.py)
- Mixer IP / port configurable from the UI — currently hardcoded
- Mute, EQ, scenes, or anything beyond fader levels

## Install (HACS)

1. Add this repo as a custom HACS repository: `Lab271/labs-homeassistant-midas`, category *Integration*.
2. Install **Midas OSC** from HACS.
3. Restart Home Assistant.
4. *Settings → Devices & Services → Add Integration → Midas OSC*. Give it a name (default `Midas`).

## Install (manual)

```bash
cd ~/.homeassistant/custom_components
git clone https://github.com/Lab271/labs-homeassistant-midas.git midas_osc
# restart Home Assistant
```

## Configuration

UI-only via the config flow. The only field is the friendly name shown in HA. Mixer connection is currently fixed in code:

| Setting | Value | Where |
| --- | --- | --- |
| Mixer IP | `10.32.8.30` | [`number.py`](number.py) |
| Mixer port | `10023` (OSC default) | [`number.py`](number.py) |
| Local port | `10024` | [`number.py`](number.py) |

## Limitations

- **Mixer address is hardcoded.** If you fork this for another setup, edit `MIXER_IP` / `MIXER_PORT` in [`number.py`](number.py). Making this UI-configurable is a planned follow-up.
- **Channel/DCA mapping is hardcoded.** The list of rooms and sends in `async_setup_entry` matches the Lab271 routing scheme; adapt the entity list for your own setup.
- **No auth.** OSC over UDP, no encryption — keep the mixer on a trusted network.

## Dependencies

- `python-osc==1.9.0` (declared in [`manifest.json`](manifest.json))

## Owner

`@LAB271` — see [labs-infra-overview](https://github.com/Lab271/labs-infra-overview) for the full Lab271 infra index and conventions.
