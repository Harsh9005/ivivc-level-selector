"""
Deconvolution methods for Level A IVIVC.

Implements Wagner-Nelson method for extracting in vivo absorption
from plasma concentration data.

All data is synthetic/hypothetical for educational purposes only.
"""

import numpy as np


def wagner_nelson(times, conc, ke):
    """
    Wagner-Nelson deconvolution for 1-compartment models.

    Calculates fraction absorbed from plasma concentration data:

    Fa(t) = [C(t) + ke · AUC(0,t)] / [ke · AUC(0,∞)]

    This method does NOT require IV reference data — only the
    elimination rate constant (ke) from the terminal phase.

    Parameters
    ----------
    times : array-like
        Time points (hours).
    conc : array-like
        Plasma concentrations at each time point.
    ke : float
        First-order elimination rate constant (h⁻¹).

    Returns
    -------
    dict
        'times': time points,
        'fraction_absorbed': Fa(t) at each time point (0 to 1),
        'auc_cumulative': cumulative AUC(0,t),
        'auc_total': AUC(0,∞),
        'amount_absorbed': C(t) + ke·AUC(0,t) (unnormalized)
    """
    times = np.asarray(times, dtype=float)
    conc = np.asarray(conc, dtype=float)

    # Cumulative AUC(0,t) using trapezoidal rule
    auc_cumulative = np.zeros_like(times)
    for i in range(1, len(times)):
        auc_cumulative[i] = auc_cumulative[i - 1] + \
            0.5 * (conc[i - 1] + conc[i]) * (times[i] - times[i - 1])

    # AUC(0,∞) = AUC(0,tlast) + C(tlast)/ke
    auc_total = auc_cumulative[-1] + conc[-1] / ke if ke > 0 else auc_cumulative[-1]

    # Amount absorbed (unnormalized)
    amount_absorbed = conc + ke * auc_cumulative

    # Fraction absorbed (normalized to 0–1)
    denom = ke * auc_total
    if denom > 0:
        fraction_absorbed = amount_absorbed / denom
    else:
        fraction_absorbed = np.zeros_like(times)

    # Clip to [0, 1] for numerical stability
    fraction_absorbed = np.clip(fraction_absorbed, 0.0, 1.0)

    return {
        'times': times,
        'fraction_absorbed': fraction_absorbed,
        'auc_cumulative': auc_cumulative,
        'auc_total': auc_total,
        'amount_absorbed': amount_absorbed,
    }


def numerical_deconvolution(times, conc, impulse_response, dt=0.1):
    """
    Numerical deconvolution using iterative point-area method.

    Given C(t) = r(t) ⊗ h(t), solve for r(t) — the in vivo input rate.

    Parameters
    ----------
    times : array-like
        Time points (hours).
    conc : array-like
        Observed plasma concentrations.
    impulse_response : array-like
        Unit impulse response h(t) at same time points.
    dt : float
        Time step for numerical computation.

    Returns
    -------
    dict
        'times': time points,
        'input_rate': estimated in vivo input rate r(t),
        'fraction_absorbed': cumulative fraction absorbed (integrated r(t))
    """
    times = np.asarray(times, dtype=float)
    conc = np.asarray(conc, dtype=float)
    h = np.asarray(impulse_response, dtype=float)

    n = len(times)
    r = np.zeros(n)

    # Iterative point-area deconvolution
    for i in range(n):
        sum_prev = 0.0
        for j in range(i):
            # Use trapezoidal approximation
            if i - j < n:
                sum_prev += r[j] * h[i - j] * (times[min(j + 1, n - 1)] - times[j])

        if h[0] > 0 and i > 0:
            time_step = times[i] - times[i - 1]
            r[i] = (conc[i] - sum_prev) / (h[0] * time_step) if time_step > 0 else 0.0
        elif i == 0 and h[0] > 0:
            r[0] = conc[0] / (h[0] * dt)

    # Ensure non-negative
    r = np.maximum(r, 0.0)

    # Cumulative fraction absorbed
    fa_cumulative = np.zeros(n)
    for i in range(1, n):
        fa_cumulative[i] = fa_cumulative[i - 1] + \
            0.5 * (r[i - 1] + r[i]) * (times[i] - times[i - 1])

    # Normalize to 0-1
    if fa_cumulative[-1] > 0:
        fa_cumulative = fa_cumulative / fa_cumulative[-1]

    return {
        'times': times,
        'input_rate': r,
        'fraction_absorbed': fa_cumulative,
    }
