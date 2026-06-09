"""utils.share — encode/decode demo-page scenarios into URL query strings.

A "scenario" is the set of sidebar-slider values that fully define what each
demo page renders. Encoding it into a query string makes a scenario shareable:
paste the URL and the page comes up with those exact slider positions.

This module is **pure** (stdlib only — NO streamlit, NO numpy). It must run
identically under pytest and under stlite/Pyodide in the browser, so the demo
pages import it and feed it ``dict(st.query_params)``.

Public surface:
    encode_scenario(values)            -> query string
    apply_schema(raw, schema)          -> typed dict (extraction helper)
    decode_scenario(qs_or_dict, schema)-> typed dict (never raises)
    SCHEMAS                            -> {page: {key: (type, default)}}
    LEVEL_A_PRESETS / LEVEL_B_PRESETS / LEVEL_C_PRESETS

Schema entry type tags: "float", "int", "str".
"""
from __future__ import annotations

from urllib.parse import urlencode, parse_qs

__all__ = [
    "encode_scenario",
    "decode_scenario",
    "apply_schema",
    "SCHEMAS",
    "LEVEL_A_PRESETS",
    "LEVEL_B_PRESETS",
    "LEVEL_C_PRESETS",
]

# Floats are rounded to this many decimals before encoding to keep URLs short
# while preserving the 0.01/0.25/0.5 slider steps used across the demo pages.
_FLOAT_DECIMALS = 3


def _fmt_value(v):
    """Stringify a scalar for the query string.

    Floats are rounded and trailing zeros trimmed (0.300 -> "0.3", 15.0 -> "15");
    everything else is passed through ``str``.
    """
    if isinstance(v, bool):
        # bool is a subclass of int — keep it explicit as 0/1 is not used here,
        # but guard so True doesn't sneak through as an int path unexpectedly.
        return str(v)
    if isinstance(v, float):
        r = round(v, _FLOAT_DECIMALS)
        if r == int(r):
            return str(int(r))
        # strip trailing zeros from the decimal part
        return f"{r:.{_FLOAT_DECIMALS}f}".rstrip("0").rstrip(".")
    return str(v)


def encode_scenario(values: dict) -> str:
    """Turn ``{key: number/str}`` into a URL query string.

    Floats are rounded to a sane precision (3 decimals) and trimmed to keep the
    URL short. Returns a string like ``"k_fast=0.3&k_slow=0.08"``. ``None``
    values are skipped. Order follows the dict's insertion order (stable).
    """
    pairs = [(k, _fmt_value(v)) for k, v in values.items() if v is not None]
    return urlencode(pairs)


def _coerce(raw_str, type_tag, default):
    """Coerce one raw string to its typed value, falling back to ``default``.

    Never raises — malformed/junk input returns ``default``.
    """
    if raw_str is None:
        return default
    s = str(raw_str).strip()
    if s == "":
        return default
    try:
        if type_tag == "float":
            return float(s)
        if type_tag == "int":
            # tolerate "300" and "300.0" alike
            return int(round(float(s)))
        # "str" or anything else → pass the raw string through
        return s
    except (ValueError, TypeError):
        return default


def apply_schema(raw: dict, schema: dict) -> dict:
    """Typed extraction helper used by :func:`decode_scenario`.

    ``raw`` is a flat ``{key: raw_string}`` mapping (values may also already be
    numbers — they get coerced regardless). ``schema`` is
    ``{key: (type_tag, default)}``. Returns ``{key: typed_value}`` for every key
    in the schema, substituting the default for missing or malformed entries.
    Extra keys in ``raw`` that aren't in the schema are ignored.
    """
    out = {}
    for key, (type_tag, default) in schema.items():
        out[key] = _coerce(raw.get(key), type_tag, default)
    return out


def _normalize_raw(query_string_or_dict) -> dict:
    """Accept a query string OR a dict of raw params → flat ``{key: str}`` dict.

    For query strings we use ``parse_qs`` and take the last value of each key
    (so ``a=1&a=2`` → ``"2"``, matching how browsers/Streamlit treat repeats).
    For dicts we accept scalar values or lists (taking the last element of a
    list), mirroring ``st.query_params`` which may surface either form.
    """
    if query_string_or_dict is None:
        return {}
    if isinstance(query_string_or_dict, str):
        parsed = parse_qs(query_string_or_dict, keep_blank_values=True)
        return {k: (v[-1] if v else "") for k, v in parsed.items()}
    # dict-like
    out = {}
    for k, v in dict(query_string_or_dict).items():
        if isinstance(v, (list, tuple)):
            out[k] = v[-1] if v else ""
        else:
            out[k] = v
    return out


def decode_scenario(query_string_or_dict, schema: dict) -> dict:
    """Decode a query string OR raw-param dict into typed values.

    Missing keys and non-numeric junk fall back to the schema default; this
    function never raises. An empty string / empty dict yields all defaults.
    """
    raw = _normalize_raw(query_string_or_dict)
    return apply_schema(raw, schema)


# =============================================================================
# Per-page schemas — keys MUST match the real slider keys on each demo page.
# Defaults MUST match the real slider default `value=`.
# =============================================================================

# Level A — pages/3_📈_Level_A_Demo.py
#   k_fast/k_medium/k_slow: ER dissolution rates; k_new: "new formulation" rate.
SCHEMA_LEVEL_A = {
    "k_fast": ("float", 0.30),    # min 0.10  max 0.60  step 0.02
    "k_medium": ("float", 0.15),  # min 0.05  max 0.40  step 0.02
    "k_slow": ("float", 0.08),    # min 0.02  max 0.25  step 0.01
    "k_new": ("float", 0.20),     # min 0.02  max 0.60  step 0.02
}

# Level B — pages/4_📊_Level_B_Demo.py
SCHEMA_LEVEL_B = {
    "b_kf": ("float", 0.30),      # min 0.10  max 0.60  step 0.02
    "b_km": ("float", 0.15),      # min 0.05  max 0.40  step 0.02
    "b_ks": ("float", 0.08),      # min 0.02  max 0.25  step 0.01
    "p1_burst": ("float", 40.0),  # min 10.0  max 70.0  step 5.0
    "p1_bk": ("float", 2.0),      # min 0.5   max 5.0   step 0.25
    "p2_k": ("float", 0.16),      # min 0.05  max 0.40  step 0.01
}

# Level C — pages/5_📉_Level_C_Demo.py
#   Fmax/τ are int sliders; Burst sliders are float.
SCHEMA_LEVEL_C = {
    "fA": ("int", 88),     # min 50  max 100 step 2
    "tA": ("int", 300),    # min 100 max 600 step 25
    "bA": ("float", 15.0), # min 0.0 max 30.0 step 1.0
    "fB": ("int", 68),     # min 40  max 90  step 2
    "tB": ("int", 420),    # min 200 max 700 step 25
    "bB": ("float", 7.0),  # min 0.0 max 20.0 step 0.5
    "fC": ("int", 58),     # min 30  max 80  step 2
    "tC": ("int", 500),    # min 300 max 800 step 25
    "bC": ("float", 4.5),  # min 0.0 max 15.0 step 0.5
}

SCHEMAS = {
    "level_a": SCHEMA_LEVEL_A,
    "level_b": SCHEMA_LEVEL_B,
    "level_c": SCHEMA_LEVEL_C,
}


# =============================================================================
# Built-in preset scenarios. Preset keys MUST be a subset of the page's schema
# keys; preset values MUST lie within each slider's min/max range.
# =============================================================================

LEVEL_A_PRESETS = {
    "Well-correlated (default)": {
        "k_fast": 0.30, "k_medium": 0.15, "k_slow": 0.08, "k_new": 0.20,
    },
    "Fast vs slow extremes": {
        # Push F1 to the top of its range and F3 to the bottom for a wide spread.
        "k_fast": 0.60, "k_medium": 0.20, "k_slow": 0.02, "k_new": 0.40,
    },
    "Near-identical formulations": {
        # All three ER rates bunched together — minimal between-formulation spread.
        "k_fast": 0.16, "k_medium": 0.15, "k_slow": 0.14, "k_new": 0.15,
    },
}

LEVEL_B_PRESETS = {
    "Well-separated profiles (default)": {
        "b_kf": 0.30, "b_km": 0.15, "b_ks": 0.08,
        "p1_burst": 40.0, "p1_bk": 2.0, "p2_k": 0.16,
    },
    "Big burst vs steady (clear difference)": {
        # Large fast burst on P1 vs a slow steady P2 → distinct shapes, MDT apart.
        "b_kf": 0.40, "b_km": 0.18, "b_ks": 0.08,
        "p1_burst": 65.0, "p1_bk": 4.0, "p2_k": 0.10,
    },
    "Converged MDT (the Level-B trap)": {
        # Tune burst/steady so P1 and P2 land on nearly the same MDT despite very
        # different shapes — demonstrates Level B's core weakness.
        "b_kf": 0.30, "b_km": 0.15, "b_ks": 0.08,
        "p1_burst": 30.0, "p1_bk": 1.5, "p2_k": 0.20,
    },
}

LEVEL_C_PRESETS = {
    "Distinct profiles (default)": {
        "fA": 88, "tA": 300, "bA": 15.0,
        "fB": 68, "tB": 420, "bB": 7.0,
        "fC": 58, "tC": 500, "bC": 4.5,
    },
    "B and C similar (f2 ≥ 50)": {
        # Bring B and C close in Fmax/τ/burst so their f2 climbs into SIMILAR.
        "fA": 88, "tA": 300, "bA": 15.0,
        "fB": 66, "tB": 480, "bB": 5.0,
        "fC": 64, "tC": 500, "bC": 4.5,
    },
    "Wide MW spread (all different)": {
        # Spread A/B/C across their ranges for maximal contrast.
        "fA": 100, "tA": 100, "bA": 28.0,
        "fB": 64, "tB": 450, "bB": 6.0,
        "fC": 32, "tC": 800, "bC": 1.0,
    },
}
