"""Tests for utils.share — scenario encode/decode + preset validation.

Pure module (stdlib only), so these tests have no streamlit/numpy dependency.
"""
import pytest

from utils import share
from utils.share import (
    encode_scenario,
    decode_scenario,
    apply_schema,
    SCHEMAS,
    LEVEL_A_PRESETS,
    LEVEL_B_PRESETS,
    LEVEL_C_PRESETS,
)


# =============================================================================
# Slider min/max recorded from the three demo pages (source of truth for the
# preset-range checks below). Keep in sync with the slider definitions in
# pages/3, pages/4, pages/5.
# =============================================================================

RANGES = {
    "level_a": {
        "k_fast": (0.10, 0.60),
        "k_medium": (0.05, 0.40),
        "k_slow": (0.02, 0.25),
        "k_new": (0.02, 0.60),
    },
    "level_b": {
        "b_kf": (0.10, 0.60),
        "b_km": (0.05, 0.40),
        "b_ks": (0.02, 0.25),
        "p1_burst": (10.0, 70.0),
        "p1_bk": (0.5, 5.0),
        "p2_k": (0.05, 0.40),
    },
    "level_c": {
        "fA": (50, 100),
        "tA": (100, 600),
        "bA": (0.0, 30.0),
        "fB": (40, 90),
        "tB": (200, 700),
        "bB": (0.0, 20.0),
        "fC": (30, 80),
        "tC": (300, 800),
        "bC": (0.0, 15.0),
    },
}

PRESETS_BY_PAGE = {
    "level_a": LEVEL_A_PRESETS,
    "level_b": LEVEL_B_PRESETS,
    "level_c": LEVEL_C_PRESETS,
}


# =============================================================================
# encode_scenario → decode_scenario round-trip
# =============================================================================

def test_roundtrip_floats_ints_str():
    schema = {
        "a": ("float", 1.0),
        "n": ("int", 5),
        "label": ("str", "x"),
    }
    values = {"a": 0.123, "n": 42, "label": "hello"}
    decoded = decode_scenario(encode_scenario(values), schema)
    assert decoded["a"] == pytest.approx(0.123, abs=1e-3)  # within float tolerance
    assert decoded["n"] == 42                              # int exact
    assert decoded["label"] == "hello"                     # str exact


def test_roundtrip_each_level_a_schema_defaults():
    schema = SCHEMAS["level_a"]
    values = {k: d for k, (t, d) in schema.items()}
    decoded = decode_scenario(encode_scenario(values), schema)
    for k, (t, d) in schema.items():
        if t == "float":
            assert decoded[k] == pytest.approx(d, abs=1e-3)
        else:
            assert decoded[k] == d


def test_roundtrip_level_c_mixed_int_float():
    schema = SCHEMAS["level_c"]
    values = {
        "fA": 90, "tA": 250, "bA": 12.5,
        "fB": 70, "tB": 400, "bB": 6.5,
        "fC": 55, "tC": 600, "bC": 3.5,
    }
    decoded = decode_scenario(encode_scenario(values), schema)
    assert decoded["fA"] == 90 and isinstance(decoded["fA"], int)
    assert decoded["tC"] == 600 and isinstance(decoded["tC"], int)
    assert decoded["bA"] == pytest.approx(12.5, abs=1e-3)
    assert isinstance(decoded["bB"], float)


def test_float_rounding_keeps_three_decimals():
    # A value with more precision than 3 decimals rounds in the URL string.
    qs = encode_scenario({"x": 0.123456})
    assert "0.123" in qs
    assert "0.1234" not in qs


def test_encode_trims_trailing_zeros():
    qs = encode_scenario({"a": 0.30, "b": 15.0})
    # 0.30 -> "0.3", 15.0 -> "15"
    assert "a=0.3" in qs
    assert "b=15" in qs and "b=15.0" not in qs


# =============================================================================
# decode_scenario robustness — defaults for missing / junk / empty
# =============================================================================

def test_decode_missing_keys_use_defaults():
    schema = {"a": ("float", 1.5), "n": ("int", 7), "s": ("str", "def")}
    decoded = decode_scenario("a=2.0", schema)
    assert decoded["a"] == pytest.approx(2.0)
    assert decoded["n"] == 7      # missing → default
    assert decoded["s"] == "def"  # missing → default


def test_decode_junk_values_fall_back_no_exception():
    schema = {"a": ("float", 1.5), "n": ("int", 7)}
    # garbage strings must not raise; they fall back to defaults
    decoded = decode_scenario("a=not_a_number&n=oops", schema)
    assert decoded["a"] == 1.5
    assert decoded["n"] == 7


def test_decode_empty_blank_values_use_defaults():
    schema = {"a": ("float", 0.5), "n": ("int", 3)}
    decoded = decode_scenario("a=&n=", schema)
    assert decoded["a"] == 0.5
    assert decoded["n"] == 3


def test_decode_empty_string_yields_all_defaults():
    for page, schema in SCHEMAS.items():
        decoded = decode_scenario("", schema)
        for k, (t, d) in schema.items():
            assert decoded[k] == d, f"{page}.{k} should default on empty string"
        assert set(decoded.keys()) == set(schema.keys())


def test_decode_empty_dict_yields_all_defaults():
    schema = SCHEMAS["level_b"]
    decoded = decode_scenario({}, schema)
    assert decoded == {k: d for k, (t, d) in schema.items()}


def test_decode_accepts_dict_input():
    schema = SCHEMAS["level_a"]
    raw = {"k_fast": "0.5", "k_slow": "0.05"}
    decoded = decode_scenario(raw, schema)
    assert decoded["k_fast"] == pytest.approx(0.5)
    assert decoded["k_slow"] == pytest.approx(0.05)
    assert decoded["k_medium"] == 0.15  # default


def test_decode_accepts_dict_with_list_values():
    # st.query_params can surface repeated params as lists — take the last.
    schema = SCHEMAS["level_a"]
    decoded = decode_scenario({"k_fast": ["0.2", "0.4"]}, schema)
    assert decoded["k_fast"] == pytest.approx(0.4)


def test_decode_ignores_extra_unknown_keys():
    schema = {"a": ("float", 1.0)}
    decoded = decode_scenario("a=2.0&bogus=99", schema)
    assert decoded == {"a": 2.0}


def test_int_coercion_tolerates_float_string():
    schema = {"n": ("int", 0)}
    assert decode_scenario("n=300.0", schema)["n"] == 300


# =============================================================================
# apply_schema directly
# =============================================================================

def test_apply_schema_typed_extraction():
    schema = {"a": ("float", 0.0), "n": ("int", 0), "s": ("str", "")}
    out = apply_schema({"a": "1.25", "n": "9", "s": "tag"}, schema)
    assert out == {"a": 1.25, "n": 9, "s": "tag"}


# =============================================================================
# Preset validation — keys present in schema, values within slider min/max
# =============================================================================

@pytest.mark.parametrize("page", ["level_a", "level_b", "level_c"])
def test_presets_only_use_schema_keys(page):
    schema = SCHEMAS[page]
    schema_keys = set(schema.keys())
    for preset_name, preset in PRESETS_BY_PAGE[page].items():
        extra = set(preset.keys()) - schema_keys
        assert not extra, f"{page} preset '{preset_name}' has non-schema keys: {extra}"


@pytest.mark.parametrize("page", ["level_a", "level_b", "level_c"])
def test_presets_values_within_slider_ranges(page):
    ranges = RANGES[page]
    for preset_name, preset in PRESETS_BY_PAGE[page].items():
        for key, val in preset.items():
            lo, hi = ranges[key]
            assert lo <= val <= hi, (
                f"{page} preset '{preset_name}' key '{key}'={val} "
                f"outside [{lo}, {hi}]"
            )


@pytest.mark.parametrize("page", ["level_a", "level_b", "level_c"])
def test_each_page_has_three_presets(page):
    assert len(PRESETS_BY_PAGE[page]) == 3


@pytest.mark.parametrize("page", ["level_a", "level_b", "level_c"])
def test_presets_roundtrip_through_url(page):
    # A preset encoded into a URL and decoded back should match within tolerance.
    schema = SCHEMAS[page]
    for preset_name, preset in PRESETS_BY_PAGE[page].items():
        decoded = decode_scenario(encode_scenario(preset), schema)
        for key, val in preset.items():
            t = schema[key][0]
            if t == "float":
                assert decoded[key] == pytest.approx(val, abs=1e-3)
            else:
                assert decoded[key] == val


def test_ranges_table_covers_every_schema_key():
    # Guard: the RANGES table in this test must stay in sync with SCHEMAS.
    for page, schema in SCHEMAS.items():
        assert set(RANGES[page].keys()) == set(schema.keys()), (
            f"RANGES[{page}] out of sync with SCHEMAS[{page}]"
        )
