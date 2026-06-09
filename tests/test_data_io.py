"""Tests for utils.data_io — the pure CSV parsing / alignment / ke-estimation module.

This module powers the "Analyze Your Own Data" page (pages/6). It must be pure
(numpy + pandas + stdlib, NO streamlit) so it can run identically under pytest
and under stlite/Pyodide in the browser.
"""
import numpy as np
import pandas as pd
import pytest

from utils import data_io as dio
from utils.data_io import DataValidationError


# =============================================================================
# parse_profile_csv
# =============================================================================

def test_parse_valid_csv_string_structure():
    csv = "time,F1,F2\n0,0,0\n1,30,20\n2,55,40\n4,80,65\n"
    out = dio.parse_profile_csv(csv)
    assert set(out.keys()) == {"times", "names", "series"}
    assert out["names"] == ["F1", "F2"]
    np.testing.assert_allclose(out["times"], [0, 1, 2, 4])
    assert isinstance(out["times"], np.ndarray)
    np.testing.assert_allclose(out["series"]["F1"], [0, 30, 55, 80])
    np.testing.assert_allclose(out["series"]["F2"], [0, 20, 40, 65])
    assert isinstance(out["series"]["F1"], np.ndarray)


def test_parse_dataframe_input_works():
    df = pd.DataFrame({"Time": [0, 1, 2], "FormA": [0.0, 10.0, 25.0]})
    out = dio.parse_profile_csv(df)
    assert out["names"] == ["FormA"]
    np.testing.assert_allclose(out["times"], [0, 1, 2])
    np.testing.assert_allclose(out["series"]["FormA"], [0, 10, 25])


def test_parse_accepts_t_and_uppercase_time_aliases():
    # 't' alias
    out_t = dio.parse_profile_csv("t,A\n0,0\n1,5\n")
    np.testing.assert_allclose(out_t["times"], [0, 1])
    assert out_t["names"] == ["A"]
    # 'TIME' alias (case-insensitive)
    out_time = dio.parse_profile_csv("TIME,A\n0,0\n1,5\n")
    np.testing.assert_allclose(out_time["times"], [0, 1])


def test_missing_time_column_raises():
    csv = "F1,F2\n0,0\n1,2\n"
    with pytest.raises(DataValidationError):
        dio.parse_profile_csv(csv)


def test_non_increasing_time_raises_with_friendly_message():
    csv = "time,F1\n0,0\n1,10\n2,20\n2,30\n"  # duplicate t=2
    with pytest.raises(DataValidationError) as exc:
        dio.parse_profile_csv(csv)
    msg = str(exc.value)
    assert "increasing" in msg.lower()


def test_decreasing_time_raises():
    csv = "time,F1\n0,0\n3,10\n2,20\n"
    with pytest.raises(DataValidationError):
        dio.parse_profile_csv(csv)


def test_negative_time_raises():
    csv = "time,F1\n-1,0\n0,10\n1,20\n"
    with pytest.raises(DataValidationError):
        dio.parse_profile_csv(csv)


def test_only_time_column_no_formulations_raises():
    csv = "time\n0\n1\n2\n"
    with pytest.raises(DataValidationError):
        dio.parse_profile_csv(csv)


def test_single_row_raises():
    csv = "time,F1\n0,0\n"
    with pytest.raises(DataValidationError):
        dio.parse_profile_csv(csv)


def test_non_numeric_cell_raises():
    csv = "time,F1\n0,0\n1,oops\n2,40\n"
    with pytest.raises(DataValidationError):
        dio.parse_profile_csv(csv)


def test_value_label_does_not_break_parse():
    # value_label is cosmetic / for downstream use; parsing still works
    out = dio.parse_profile_csv("time,F1\n0,0\n1,50\n", value_label="% released")
    assert out["names"] == ["F1"]


# =============================================================================
# align_dissolution_to_pk
# =============================================================================

def test_align_interpolates_known_midpoint():
    # dissolution at t=0,2,4 -> 0,40,80 ; PK grid includes t=1 and t=3
    diss = dio.parse_profile_csv("time,F1\n0,0\n2,40\n4,80\n")
    pk = dio.parse_profile_csv("time,F1\n0,0\n1,1.0\n3,2.0\n")
    aligned = dio.align_dissolution_to_pk(diss, pk)
    assert aligned["names"] == ["F1"]
    np.testing.assert_allclose(aligned["pk_times"], [0, 1, 3])
    # linear interp of dissolution at pk times: t=1 -> 20, t=3 -> 60
    np.testing.assert_allclose(aligned["dissolved"]["F1"], [0, 20, 60])
    np.testing.assert_allclose(aligned["conc"]["F1"], [0, 1.0, 2.0])
    assert aligned["warnings"] == []


def test_align_name_mismatch_emits_warning_and_aligns_by_order():
    diss = dio.parse_profile_csv("time,DISS_A\n0,0\n2,40\n4,80\n")
    pk = dio.parse_profile_csv("time,PK_A\n0,0\n1,1.0\n3,2.0\n")
    aligned = dio.align_dissolution_to_pk(diss, pk)
    assert aligned["warnings"], "expected a warning when names differ"
    # aligned by order -> uses the PK name and still interpolates the dissolution
    assert len(aligned["names"]) == 1
    name = aligned["names"][0]
    np.testing.assert_allclose(aligned["dissolved"][name], [0, 20, 60])
    np.testing.assert_allclose(aligned["conc"][name], [0, 1.0, 2.0])


def test_align_matches_common_names_when_some_overlap():
    diss = dio.parse_profile_csv("time,F1,F2\n0,0,0\n2,40,30\n4,80,60\n")
    pk = dio.parse_profile_csv("time,F1,F2\n0,0,0\n1,1.0,0.5\n3,2.0,1.0\n")
    aligned = dio.align_dissolution_to_pk(diss, pk)
    assert set(aligned["names"]) == {"F1", "F2"}
    assert aligned["warnings"] == []
    np.testing.assert_allclose(aligned["dissolved"]["F1"], [0, 20, 60])
    np.testing.assert_allclose(aligned["dissolved"]["F2"], [0, 15, 45])


# =============================================================================
# estimate_ke
# =============================================================================

def test_estimate_ke_recovers_known_value():
    ke_true = 0.15
    c0 = 10.0
    # a rising-then-falling profile; estimate_ke should use the descending tail
    times = np.array([0.0, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0])
    # pure decay from the peak region (build a realistic up-then-down curve)
    conc = c0 * np.exp(-ke_true * times)  # monotone decay -> tail is clean
    ke_est = dio.estimate_ke(times, conc)
    assert abs(ke_est - ke_true) < 0.01


def test_estimate_ke_uses_descending_tail_of_pk_curve():
    ke_true = 0.12
    times = np.array([0.0, 0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 16.0])
    # one-compartment-like: rise then fall
    ka = 1.2
    conc = 100.0 * (np.exp(-ke_true * times) - np.exp(-ka * times))
    ke_est = dio.estimate_ke(times, conc)
    # terminal slope recovers ke within tolerance
    assert abs(ke_est - ke_true) < 0.03


def test_estimate_ke_too_few_points_raises():
    with pytest.raises(DataValidationError):
        dio.estimate_ke(np.array([1.0]), np.array([5.0]))


def test_estimate_ke_nonpositive_tail_raises():
    # all-zero tail cannot be log-fit
    times = np.array([0.0, 1.0, 2.0, 3.0])
    conc = np.array([0.0, 0.0, 0.0, 0.0])
    with pytest.raises(DataValidationError):
        dio.estimate_ke(times, conc)


# =============================================================================
# templates & examples round-trip
# =============================================================================

def test_dissolution_template_roundtrips():
    csv = dio.dissolution_template_csv()
    out = dio.parse_profile_csv(csv)
    assert len(out["names"]) >= 1
    assert len(out["times"]) >= 2


def test_pk_template_roundtrips():
    csv = dio.pk_template_csv()
    out = dio.parse_profile_csv(csv)
    assert len(out["names"]) >= 1
    assert len(out["times"]) >= 2


def test_example_dissolution_roundtrips_three_formulations():
    csv = dio.example_dissolution_csv()
    out = dio.parse_profile_csv(csv)
    assert len(out["names"]) == 3
    assert len(out["times"]) >= 5
    # dissolution rises over time for at least one formulation
    first = out["series"][out["names"][0]]
    assert first[-1] > first[0]


def test_example_pk_roundtrips_three_formulations():
    csv = dio.example_pk_csv()
    out = dio.parse_profile_csv(csv)
    assert len(out["names"]) == 3
    assert len(out["times"]) >= 5


def test_example_diss_and_pk_align_by_name():
    diss = dio.parse_profile_csv(dio.example_dissolution_csv())
    pk = dio.parse_profile_csv(dio.example_pk_csv())
    aligned = dio.align_dissolution_to_pk(diss, pk)
    assert len(aligned["names"]) == 3
    assert aligned["warnings"] == []
    # every aligned dissolution array is on the PK time grid
    for name in aligned["names"]:
        assert len(aligned["dissolved"][name]) == len(aligned["pk_times"])
        assert len(aligned["conc"][name]) == len(aligned["pk_times"])


def test_example_ke_estimable_from_pk():
    pk = dio.parse_profile_csv(dio.example_pk_csv())
    first = pk["names"][0]
    ke = dio.estimate_ke(pk["times"], pk["series"][first])
    assert 0.001 < ke < 2.0
