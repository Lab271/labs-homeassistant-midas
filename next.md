# Next

> **State:** Private HA custom integration. All spec-fixes from the 2026-04-29 pass landed on `up-to-spec/2026-04-29` and were pushed to origin; topics + description aligned with CONVENTIONS.md (`av` dropped, description set). Pre-public audit clean — `10.32.8.30` replaced with TEST-NET-1 placeholder. Public flip and config-flow rewrite both deferred per cross-cutting decisions.
> **Last updated:** 2026-04-29
> **Source of truth:** ~/Developer/labs-infra-overview/CONVENTIONS.md

## Pending

- [ ] Open PR from `up-to-spec/2026-04-29` -> `main` and merge once reviewed (solo-maintainer self-merge OK per conventions)
- [ ] Pre-public audit + flip to public — audit is clean post-genericization; flip itself deferred per CONVENTIONS.md "keep private until the lab is up to spec"
- [ ] (Deferred) Replace hardcoded topology with config-flow-driven IP/port + entity mapping so the integration is genuinely reusable outside Lab271. For now, ships as a fork-and-edit reference (README + inline `EDIT BEFORE USE` comment frame it that way)

## Decisions needed

_(none open — all three open questions from the prior pass were resolved by the 2026-04-29 cross-cutting decisions: drop `av`, genericize IP to TEST-NET-1, defer config-flow rewrite.)_

## Recently done

- [x] 2026-04-29 — Branch `up-to-spec/2026-04-29` created and pushed; four commits: `784c9cf` (manifest Amplifier->Mixer), `e1295ad` (number.py edit-before-use comment + IP -> 192.0.2.30 TEST-NET-1), `3729c45` (CODEOWNERS), `de1c708` (README)
- [x] 2026-04-29 — `10.32.8.30` replaced with `192.0.2.30` (TEST-NET-1) in `number.py`; README references kept as-is (informational only)
- [x] 2026-04-29 — GitHub topic `av` dropped (`gh repo edit --remove-topic av`); current topics: `homeassistant`, `infrastructure`, `lab271`, `status-wip`
- [x] 2026-04-29 — GitHub description set to "Home Assistant custom integration for the Midas M32 digital mixer over OSC"
- [x] 2026-04-29 — Initial commit `c4974cd` pushed to `Lab271/labs-homeassistant-midas`
- [x] 2026-04-29 — README authored with all 7 standard sections
- [x] 2026-04-29 — `manifest.json` fixed: "Midas M32C Amplifier" -> "Midas M32C Mixer"
- [x] 2026-04-29 — `MIXER_IP`/`MIXER_PORT` documented as edit-before-use in `number.py`
- [x] 2026-04-29 — `.github/CODEOWNERS` created with `* @LAB271`
- [x] 2026-04-29 — Pre-public secrets grep: clean post-genericization (only RFC1918 reference remaining is `10.32.8.30` in `README.md:45`, which is informational and OK to keep per cross-cutting decision)

## Deviations from CONVENTIONS.md

- **Org casing (`LAB271` vs `Lab271`)** — origin URL still uses uppercase `LAB271`. Cosmetic, GitHub URLs are case-insensitive. Skipped this pass.
- **Config-flow rewrite deferred** — current code is genuinely Lab271-only (channel numbers, DCA assignments, room names hardcoded). Shipping as fork-and-edit reference; rewrite is a follow-up.
- **Public flip deferred** — per TODO.md / cross-cutting decision; keep private until the lab is up to spec.

## Notes

- **Local folder name == GitHub repo name** (`labs-homeassistant-midas`). No divergence.
- **Last push to origin:** 2026-04-29, branch `up-to-spec/2026-04-29`. Repo not archived. Default branch `main`.
