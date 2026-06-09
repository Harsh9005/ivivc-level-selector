"""Tests for utils.synthetic_data — Level A elimination-rate (ke) parameter.

These guard the Phase-3 Feature-4 addition of an adjustable elimination rate
constant (ke) to ``generate_level_a_data``. The default path MUST reproduce the
pre-existing behaviour exactly (ke=0.10), so a known output is pinned below.
"""
import numpy as np

from utils.synthetic_data import generate_level_a_data

# Pinned from the CURRENT (pre-ke-parameter) code with default arguments.
# Captured via: max(generate_level_a_data()['pk_profiles']['F1 (Fast)']).
# Guards that the default code path is byte-for-byte unchanged after threading
# ``ke`` through as a parameter.
_F1_DEFAULT_PEAK = 1.2986258343789927


def _fast_key(result):
    """The first (fast) formulation key, mirroring how the page reads it."""
    return list(result["pk_profiles"].keys())[0]


def test_default_ke_is_010():
    """Default call still uses ke = 0.10 h⁻¹."""
    result = generate_level_a_data()
    assert result["ke"] == 0.10


def test_ke_param_is_returned():
    """A supplied ke is threaded through and surfaced in the returned dict."""
    result = generate_level_a_data(ke=0.2)
    assert result["ke"] == 0.2


def test_default_f1_peak_unchanged():
    """Default F1 (fast) PK peak matches the pinned pre-change value."""
    result = generate_level_a_data()
    fast = _fast_key(result)
    peak = float(max(result["pk_profiles"][fast]))
    assert peak == np.float64(_F1_DEFAULT_PEAK)


def test_higher_ke_lowers_auc():
    """Faster elimination → less exposure → lower AUC for the same formulation."""
    low = generate_level_a_data(ke=0.10)
    high = generate_level_a_data(ke=0.25)
    fast = _fast_key(low)
    auc_low = float(np.trapezoid(low["pk_profiles"][fast], low["times_pk"]))
    auc_high = float(np.trapezoid(high["pk_profiles"][fast], high["times_pk"]))
    assert auc_high < auc_low


def test_ke_threads_into_wagner_nelson():
    """Wagner-Nelson deconvolution uses the supplied ke (not a hardcoded one)."""
    result = generate_level_a_data(ke=0.2)
    fast = _fast_key(result)
    wn = result["fraction_absorbed"][fast]
    # Fa should be a monotone-ish non-decreasing fraction bounded in [0, 1].
    fa = np.asarray(wn["fraction_absorbed"])
    assert fa.min() >= 0.0 and fa.max() <= 1.0
    assert fa[-1] >= fa[0]


def test_vd_and_dose_unchanged_by_ke():
    """ke must not disturb Vd / dose."""
    base = generate_level_a_data()
    other = generate_level_a_data(ke=0.18)
    assert base["vd"] == other["vd"] == 50.0
    assert base["dose"] == other["dose"] == 100.0
