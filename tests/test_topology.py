"""Tests for the topology builder.

``build_entity_specs`` is pure, so these run without a Home Assistant instance.
Run with: uv run pytest
"""

import pytest

from custom_components.midas_osc.topology import build_entity_specs, make_id


def out(id_, label, dca, bus):
    return {"id": id_, "label": label, "dca": dca, "bus": bus}


def src(id_, label, ch_l, ch_r=None, default=0.75):
    entry = {"id": id_, "label": label, "ch_l": ch_l, "default": default}
    if ch_r:
        entry["ch_r"] = ch_r
    return entry


# The Lab271 install as it was hardcoded in number.py before this refactor.
LEGACY_OPTIONS = {
    "outputs": [
        out("space", "Space", 1, 1),
        out("desks", "Desks", 2, 3),
        out("makerspace", "Makerspace", 3, 5),
    ],
    "inputs": [
        src("ar_desks", "AR Desks", 9, 10),
        src("ar_space", "AR Space", 11, 12),
        src("ar_maker", "AR Maker", 13, 14),
        src("pc", "PC", 15, 16),
    ],
    "output_default": 0.35,
}

# Verbatim from the pre-refactor async_setup_entry.
LEGACY_PATHS = [
    ("/dca/1/fader",),
    ("/dca/2/fader",),
    ("/dca/3/fader",),
    ("/ch/09/mix/01/level", "/ch/10/mix/01/level"),
    ("/ch/09/mix/03/level", "/ch/10/mix/03/level"),
    ("/ch/09/mix/05/level", "/ch/10/mix/05/level"),
    ("/ch/11/mix/01/level", "/ch/12/mix/01/level"),
    ("/ch/11/mix/03/level", "/ch/12/mix/03/level"),
    ("/ch/11/mix/05/level", "/ch/12/mix/05/level"),
    ("/ch/13/mix/01/level", "/ch/14/mix/01/level"),
    ("/ch/13/mix/03/level", "/ch/14/mix/03/level"),
    ("/ch/13/mix/05/level", "/ch/14/mix/05/level"),
    ("/ch/15/mix/01/level", "/ch/16/mix/01/level"),
    ("/ch/15/mix/03/level", "/ch/16/mix/03/level"),
    ("/ch/15/mix/05/level", "/ch/16/mix/05/level"),
]


def test_reproduces_legacy_topology():
    """The config-driven builder emits exactly the old hardcoded OSC paths."""
    specs = build_entity_specs(LEGACY_OPTIONS)
    assert [s.paths for s in specs] == LEGACY_PATHS


def test_legacy_labels_and_keys():
    specs = build_entity_specs(LEGACY_OPTIONS)
    assert specs[0].label == "Space"
    assert specs[0].key == "fader_space"
    assert specs[3].label == "AR Desks → Space"
    assert specs[3].key == "send_ar_desks_space"


def test_entity_count_is_outputs_plus_matrix():
    specs = build_entity_specs(LEGACY_OPTIONS)
    assert len(specs) == 3 + (4 * 3)


def test_keys_are_unique():
    specs = build_entity_specs(LEGACY_OPTIONS)
    assert len({s.key for s in specs}) == len(specs)


def test_fader_uses_output_default_and_send_uses_input_default():
    specs = build_entity_specs(LEGACY_OPTIONS)
    faders = [s for s in specs if s.key.startswith("fader_")]
    sends = [s for s in specs if s.key.startswith("send_")]
    assert all(s.default == 0.35 for s in faders)
    assert all(s.default == 0.75 for s in sends)


def test_output_default_falls_back_when_absent():
    options = {**LEGACY_OPTIONS}
    options.pop("output_default")
    faders = [s for s in build_entity_specs(options) if s.key.startswith("fader_")]
    assert all(s.default == 0.35 for s in faders)


@pytest.mark.parametrize("ch_r", [None, 0])
def test_mono_input_produces_one_path(ch_r):
    """No right channel (absent or zero) means a single OSC path per send."""
    options = {
        "outputs": [out("space", "Space", 1, 1)],
        "inputs": [
            {
                "id": "mic",
                "label": "Mic",
                "ch_l": 7,
                "default": 0.5,
                **({"ch_r": ch_r} if ch_r is not None else {}),
            }
        ],
    }
    sends = [s for s in build_entity_specs(options) if s.key.startswith("send_")]
    assert len(sends) == 1
    assert sends[0].paths == ("/ch/07/mix/01/level",)
    assert sends[0].primary_path == "/ch/07/mix/01/level"
    assert sends[0].default == 0.5


def test_no_inputs_yields_faders_only():
    options = {"outputs": [out("space", "Space", 1, 1)], "inputs": []}
    specs = build_entity_specs(options)
    assert len(specs) == 1
    assert specs[0].key == "fader_space"


def test_empty_topology_yields_nothing():
    assert build_entity_specs({}) == []


def test_no_outputs_yields_nothing_even_with_inputs():
    """A send needs a destination; inputs alone produce no entities."""
    options = {"outputs": [], "inputs": [src("pc", "PC", 15, 16)]}
    assert build_entity_specs(options) == []


def test_two_digit_channels_and_buses_are_not_over_padded():
    options = {
        "outputs": [out("big", "Big", 16, 16)],
        "inputs": [src("hi", "Hi", 31, 32)],
    }
    sends = [s for s in build_entity_specs(options) if s.key.startswith("send_")]
    assert sends[0].paths == ("/ch/31/mix/16/level", "/ch/32/mix/16/level")


def test_dca_is_not_zero_padded():
    """DCA paths use the bare number: /dca/1/fader, not /dca/01/fader."""
    specs = build_entity_specs({"outputs": [out("a", "A", 1, 1)]})
    assert specs[0].paths == ("/dca/1/fader",)


class TestMakeId:
    def test_slugifies(self):
        assert make_id("AR Desks", []) == "ar_desks"

    def test_dedupes_with_numeric_suffix(self):
        existing = [{"id": "space"}]
        assert make_id("Space", existing) == "space_2"

    def test_dedupes_repeatedly(self):
        existing = [{"id": "space"}, {"id": "space_2"}]
        assert make_id("Space", existing) == "space_3"

    def test_falls_back_when_label_has_no_slug_characters(self):
        """slugify() gives every unsluggable label the same base, so dedupe still applies."""
        assert make_id("→", []) == "unknown"
        assert make_id("→", [{"id": "unknown"}]) == "unknown_2"
