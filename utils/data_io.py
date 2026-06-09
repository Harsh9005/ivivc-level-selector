"""Parsing, validation, alignment and ke-estimation for user-supplied IVIVC data.

This module powers the "Analyze Your Own Data" page. It is deliberately PURE —
only numpy + pandas + the standard library, with NO streamlit import — so the
exact same code runs under pytest and inside the stlite/Pyodide browser runtime.

The user supplies two CSVs:
  * a dissolution profile (time + one column per formulation, % released), and
  * a PK profile (time + one column per formulation, plasma concentration).

Functions here turn raw CSV text (or a DataFrame) into validated numpy arrays,
interpolate dissolution onto the PK time grid, and estimate the elimination
rate constant (ke) from the terminal PK slope. Any user-facing problem raises a
DataValidationError carrying a clear, friendly message.

All synthetic example data is clearly hypothetical and for methodology only.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

# Column names (any case) that are accepted as the time column.
_TIME_ALIASES = {"time", "t"}


class DataValidationError(ValueError):
    """Raised when user-supplied data fails validation.

    The message is intended to be shown verbatim to a non-programmer user, so
    it should always be specific and friendly (e.g. naming the offending row).
    """


# =============================================================================
# Parsing
# =============================================================================

def _to_dataframe(source) -> pd.DataFrame:
    """Coerce a CSV string or DataFrame into a DataFrame (raising on garbage)."""
    if isinstance(source, pd.DataFrame):
        return source.copy()
    if isinstance(source, str):
        text = source.strip()
        if not text:
            raise DataValidationError(
                "No data provided — paste or upload a CSV with a time column "
                "and at least one formulation column."
            )
        try:
            return pd.read_csv(io.StringIO(text))
        except Exception as exc:  # pragma: no cover - defensive
            raise DataValidationError(
                f"Could not read the CSV text. Check the formatting "
                f"(comma-separated, one header row). Details: {exc}"
            )
    raise DataValidationError(
        "Unsupported input — provide CSV text (a string) or a pandas DataFrame."
    )


def parse_profile_csv(source, value_label: str = "value") -> dict:
    """Parse a profile CSV (or DataFrame) into validated arrays.

    The first column is the time column. It must be named one of
    ``time``/``Time``/``t`` (case-insensitive); if the header does not match an
    alias but the first column is clearly numeric, it is accepted as time only
    when explicitly labelled — otherwise a DataValidationError is raised. Each
    remaining column is one formulation series (header = formulation name).

    Validation:
      * at least 2 rows,
      * at least 1 non-time (formulation) column,
      * all values numeric,
      * time strictly increasing and >= 0.

    Parameters
    ----------
    source : str | pandas.DataFrame
        CSV text or a DataFrame.
    value_label : str
        Cosmetic label for the series (e.g. "% released" or "concentration").
        Accepted for caller convenience; not part of the returned structure.

    Returns
    -------
    dict
        {"times": np.ndarray, "names": [str], "series": {name: np.ndarray}}
    """
    df = _to_dataframe(source)

    if df.shape[1] < 1:
        raise DataValidationError("The data has no columns.")

    # --- identify the time column (must be the first column) -----------------
    first_col = str(df.columns[0])
    if first_col.strip().lower() not in _TIME_ALIASES:
        raise DataValidationError(
            "Missing a time column. The first column must be named "
            "'time', 'Time' or 't'. "
            f"Found '{first_col}' instead — rename the first column to 'time'."
        )

    if df.shape[1] < 2:
        raise DataValidationError(
            "Only a time column was found — add at least one formulation "
            "column (e.g. 'time,F1,F2,F3' with a value in each formulation "
            "column per row)."
        )

    if len(df) < 2:
        raise DataValidationError(
            "Need at least 2 rows (time points) to define a profile — "
            f"found {len(df)}."
        )

    # --- numeric coercion (catches non-numeric cells) ------------------------
    time_raw = df.iloc[:, 0]
    times = pd.to_numeric(time_raw, errors="coerce").to_numpy(dtype=float)
    bad_time = np.where(np.isnan(times))[0]
    if bad_time.size:
        r = int(bad_time[0])
        raise DataValidationError(
            f"The time column has a non-numeric value in row {r + 2} "
            f"('{time_raw.iloc[r]}'). Time values must be numbers."
        )

    names = [str(c) for c in df.columns[1:]]
    series: dict[str, np.ndarray] = {}
    for col in df.columns[1:]:
        col_raw = df[col]
        vals = pd.to_numeric(col_raw, errors="coerce").to_numpy(dtype=float)
        bad = np.where(np.isnan(vals))[0]
        if bad.size:
            r = int(bad[0])
            raise DataValidationError(
                f"Column '{col}' has a non-numeric value in row {r + 2} "
                f"('{col_raw.iloc[r]}'). All values must be numbers."
            )
        series[str(col)] = vals

    # --- time validation: >= 0 and strictly increasing ----------------------
    if times[0] < 0:
        raise DataValidationError(
            f"Time values must be >= 0 — the first time is {times[0]:g}."
        )
    for i in range(1, len(times)):
        if times[i] <= times[i - 1]:
            raise DataValidationError(
                "Time column must be strictly increasing — "
                f"row {i + 2} (t={times[i]:g}) is not greater than "
                f"row {i + 1} (t={times[i - 1]:g})."
            )

    # value_label is accepted for caller convenience but is intentionally not
    # part of the returned contract (callers track labels themselves).
    _ = value_label
    return {
        "times": times,
        "names": names,
        "series": series,
    }


# =============================================================================
# Alignment
# =============================================================================

def align_dissolution_to_pk(diss: dict, pk: dict) -> dict:
    """Interpolate dissolution %released onto the PK time grid, per formulation.

    Formulations are matched by exact name when the two name-sets are equal.
    If they differ, formulations are matched by ORDER (position) instead, and a
    human-readable note is appended to the returned "warnings" list.

    For each matched formulation the dissolution series is linearly interpolated
    (``np.interp``) onto the PK time grid so that dissolution and concentration
    share the same x-axis.

    Returns
    -------
    dict
        {"names": [...], "pk_times": np.ndarray,
         "dissolved": {name: arr_on_pk_times},
         "conc": {name: arr}, "warnings": [str]}
    """
    warnings: list[str] = []
    pk_times = np.asarray(pk["times"], dtype=float)
    diss_times = np.asarray(diss["times"], dtype=float)

    diss_names = list(diss["names"])
    pk_names = list(pk["names"])

    if set(diss_names) == set(pk_names) and diss_names:
        # exact-name match (use PK ordering for a stable output order)
        pairs = [(n, n) for n in pk_names]
    else:
        # match by order over the common count
        n_common = min(len(diss_names), len(pk_names))
        if n_common == 0:
            raise DataValidationError(
                "No formulations to align — both files need at least one "
                "formulation column."
            )
        pairs = [(diss_names[i], pk_names[i]) for i in range(n_common)]
        warnings.append(
            "Dissolution and PK formulation names do not match "
            f"(dissolution: {diss_names}; PK: {pk_names}). "
            f"Matched the first {n_common} formulation(s) by column order. "
            "Rename the columns to match if this is not what you intended."
        )
        if len(diss_names) != len(pk_names):
            warnings.append(
                f"Different formulation counts (dissolution has "
                f"{len(diss_names)}, PK has {len(pk_names)}); "
                f"only {n_common} could be aligned."
            )

    names: list[str] = []
    dissolved: dict[str, np.ndarray] = {}
    conc: dict[str, np.ndarray] = {}
    for diss_name, pk_name in pairs:
        out_name = pk_name  # PK name is the canonical label downstream
        diss_on_pk = np.interp(pk_times, diss_times, diss["series"][diss_name])
        names.append(out_name)
        dissolved[out_name] = diss_on_pk
        conc[out_name] = np.asarray(pk["series"][pk_name], dtype=float)

    return {
        "names": names,
        "pk_times": pk_times,
        "dissolved": dissolved,
        "conc": conc,
        "warnings": warnings,
    }


# =============================================================================
# ke estimation
# =============================================================================

def estimate_ke(times, conc) -> float:
    """Estimate the elimination rate constant ke from the terminal PK slope.

    Performs a log-linear regression (least-squares fit of ln C vs t) over the
    terminal points of the descending tail. The tail is taken as the last 3
    points after the peak, or the last half of the post-peak points when fewer
    than 3 are available. ke = -slope.

    Raises
    ------
    DataValidationError
        If there are too few usable points or the tail concentrations are not
        positive (cannot take a logarithm).
    """
    times = np.asarray(times, dtype=float)
    conc = np.asarray(conc, dtype=float)

    if times.size < 2 or conc.size < 2:
        raise DataValidationError(
            "Need at least 2 PK time points to estimate ke from the terminal "
            "slope."
        )

    # Restrict to the descending tail: everything at/after the peak.
    peak_idx = int(np.argmax(conc))
    tail_t = times[peak_idx:]
    tail_c = conc[peak_idx:]

    # Choose how many terminal points to fit.
    if tail_t.size >= 3:
        n_pts = 3
    else:
        n_pts = max(2, tail_t.size // 2)
    n_pts = min(n_pts, tail_t.size)

    fit_t = tail_t[-n_pts:]
    fit_c = tail_c[-n_pts:]

    if fit_t.size < 2:
        raise DataValidationError(
            "Not enough points on the descending tail to estimate ke. "
            "Provide more PK time points after the peak, or enter ke manually."
        )

    if np.any(fit_c <= 0):
        raise DataValidationError(
            "Cannot estimate ke — the terminal PK concentrations include "
            "non-positive values (a logarithm is required). Enter ke manually "
            "or provide positive tail concentrations."
        )

    slope, _intercept = np.polyfit(fit_t, np.log(fit_c), 1)
    ke = -float(slope)

    if not np.isfinite(ke) or ke <= 0:
        raise DataValidationError(
            "Could not estimate a positive ke from the terminal slope "
            f"(got {ke:g}). The concentration may not be declining at the end "
            "— enter ke manually instead."
        )

    return ke


# =============================================================================
# Template CSVs (downloadable starting points)
# =============================================================================

def dissolution_template_csv() -> str:
    """A small dissolution template CSV (time + F1,F2,F3, % released)."""
    return (
        "time,F1,F2,F3\n"
        "0,0,0,0\n"
        "1,35,22,12\n"
        "2,58,40,22\n"
        "4,82,63,40\n"
        "8,95,82,62\n"
        "12,99,92,76\n"
        "24,100,98,90\n"
    )


def pk_template_csv() -> str:
    """A small PK template CSV (time + F1,F2,F3, plasma concentration)."""
    return (
        "time,F1,F2,F3\n"
        "0,0,0,0\n"
        "1,3.1,2.0,1.1\n"
        "2,4.2,3.1,1.9\n"
        "4,3.8,3.6,2.7\n"
        "8,2.4,2.9,2.8\n"
        "12,1.4,1.9,2.2\n"
        "24,0.4,0.6,0.9\n"
    )


# =============================================================================
# Synthetic example dataset ("Load example" button)
# =============================================================================

# Three extended-release formulations with progressively slower release. The
# numbers below are generated once from the project's own dissolution/PK models
# (first_order_release and one_compartment_oral) and frozen here as plain CSV so
# this module stays import-light and the example is byte-stable. They are CLEARLY
# SYNTHETIC and exist only to demonstrate the analysis workflow.

_EXAMPLE_DISS_TIMES = np.array([0, 0.5, 1, 2, 4, 6, 8, 12, 16, 24], dtype=float)
_EXAMPLE_PK_TIMES = np.array([0, 0.5, 1, 2, 4, 6, 8, 12, 16, 20, 24], dtype=float)
# Per-formulation dissolution rate constants (h^-1) — Fast / Medium / Slow.
_EXAMPLE_DISS_K = {"F1 (Fast)": 0.45, "F2 (Medium)": 0.20, "F3 (Slow)": 0.10}
# PK constants shared across formulations (1-compartment oral, ke=0.12).
_EXAMPLE_KE = 0.12
_EXAMPLE_VD = 50.0
_EXAMPLE_DOSE = 100.0


def _example_dissolution_table() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    from .dissolution_models import first_order_release
    series = {
        name: np.round(first_order_release(_EXAMPLE_DISS_TIMES, k, f_max=100.0), 1)
        for name, k in _EXAMPLE_DISS_K.items()
    }
    return _EXAMPLE_DISS_TIMES, series


def _example_pk_table() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    from .pk_models import one_compartment_oral
    series = {}
    for name, k in _EXAMPLE_DISS_K.items():
        # absorption rate scales with dissolution rate (dissolution-limited)
        ka = max(k * 1.6, _EXAMPLE_KE * 1.5 + 0.01)
        conc = one_compartment_oral(
            _EXAMPLE_PK_TIMES, _EXAMPLE_DOSE, ka, _EXAMPLE_KE, _EXAMPLE_VD
        )
        series[name] = np.round(conc, 3)
    return _EXAMPLE_PK_TIMES, series


def _table_to_csv(times: np.ndarray, series: dict[str, np.ndarray]) -> str:
    names = list(series.keys())
    header = "time," + ",".join(names)
    lines = [header]
    for i, t in enumerate(times):
        row = [f"{t:g}"] + [f"{series[n][i]:g}" for n in names]
        lines.append(",".join(row))
    return "\n".join(lines) + "\n"


def example_dissolution_csv() -> str:
    """Synthetic 3-formulation dissolution example (0-24 h, % released)."""
    times, series = _example_dissolution_table()
    return _table_to_csv(times, series)


def example_pk_csv() -> str:
    """Synthetic 3-formulation PK example (0-24 h, plasma concentration)."""
    times, series = _example_pk_table()
    return _table_to_csv(times, series)
