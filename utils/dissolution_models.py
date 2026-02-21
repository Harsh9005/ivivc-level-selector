"""
Dissolution models for synthetic in vitro release data generation.

All data is synthetic/hypothetical for educational purposes only.
"""

import numpy as np

# NumPy 2.0 removed np.trapz → np.trapezoid
_trapz = getattr(np, 'trapezoid', None) or np.trapz


def first_order_release(t, k, f_max=100.0):
    """
    First-order dissolution model.

    F(t) = f_max * (1 - exp(-k * t))

    Parameters
    ----------
    t : array-like
        Time points (hours).
    k : float
        First-order rate constant (h⁻¹).
    f_max : float
        Maximum fraction released (%).

    Returns
    -------
    np.ndarray
        Cumulative % released at each time point.
    """
    t = np.asarray(t, dtype=float)
    return f_max * (1.0 - np.exp(-k * t))


def weibull_release(t, fmax, tau, beta, burst_frac=0.0, burst_tau=1.0):
    """
    Weibull dissolution model with optional burst release term.

    F(t) = burst_frac * (1 - exp(-t/burst_tau))
           + (fmax - burst_frac) * (1 - exp(-(t/tau)^beta))

    Parameters
    ----------
    t : array-like
        Time points (hours).
    fmax : float
        Maximum total release (%).
    tau : float
        Scale parameter (hours).
    beta : float
        Shape parameter (dimensionless).
    burst_frac : float
        Fraction released in burst phase (%).
    burst_tau : float
        Burst time constant (hours).

    Returns
    -------
    np.ndarray
        Cumulative % released at each time point.
    """
    t = np.asarray(t, dtype=float)
    burst = burst_frac * (1.0 - np.exp(-t / burst_tau))
    sustained = (fmax - burst_frac) * (1.0 - np.exp(-((t / tau) ** beta)))
    return burst + sustained


def higuchi_release(t, k_h, f_max=100.0):
    """
    Higuchi square-root model (matrix diffusion).

    F(t) = k_h * sqrt(t), capped at f_max.

    Parameters
    ----------
    t : array-like
        Time points (hours).
    k_h : float
        Higuchi rate constant (%·h⁻⁰·⁵).
    f_max : float
        Maximum fraction released (%).

    Returns
    -------
    np.ndarray
        Cumulative % released at each time point.
    """
    t = np.asarray(t, dtype=float)
    release = k_h * np.sqrt(t)
    return np.minimum(release, f_max)


def compute_mdt(times, release):
    """
    Compute Mean Dissolution Time (MDT) from release profile.

    MDT = Σ(t_mid * ΔF) / Σ(ΔF)

    Parameters
    ----------
    times : array-like
        Time points (hours).
    release : array-like
        Cumulative % released.

    Returns
    -------
    float
        Mean dissolution time (hours).
    """
    times = np.asarray(times, dtype=float)
    release = np.asarray(release, dtype=float)

    delta_f = np.diff(release)
    t_mid = (times[:-1] + times[1:]) / 2.0

    if np.sum(delta_f) == 0:
        return 0.0

    return np.sum(t_mid * delta_f) / np.sum(delta_f)


def compute_de(times, release):
    """
    Compute Dissolution Efficiency (DE).

    DE = AUC(dissolution) / (max_release * t_max) * 100

    Parameters
    ----------
    times : array-like
        Time points (hours).
    release : array-like
        Cumulative % released.

    Returns
    -------
    float
        Dissolution efficiency (%).
    """
    times = np.asarray(times, dtype=float)
    release = np.asarray(release, dtype=float)

    auc = _trapz(release, times)
    max_possible = release[-1] * (times[-1] - times[0])

    if max_possible == 0:
        return 0.0

    return (auc / max_possible) * 100.0


def compute_f1_f2(ref_profile, test_profile):
    """
    Compute f1 (difference factor) and f2 (similarity factor).

    FDA/EMA regulatory framework for dissolution comparison.

    f1 = [Σ|Rt - Tt| / ΣRt] × 100
    f2 = 50 × log10{[1 + (1/n)Σ(Rt - Tt)²]^(-0.5) × 100}

    Parameters
    ----------
    ref_profile : array-like
        Reference dissolution profile (% released).
    test_profile : array-like
        Test dissolution profile (% released).

    Returns
    -------
    tuple
        (f1, f2) — difference and similarity factors.
    """
    ref = np.asarray(ref_profile, dtype=float)
    test = np.asarray(test_profile, dtype=float)

    n = len(ref)
    diff = np.abs(ref - test)

    # f1 — difference factor
    f1 = (np.sum(diff) / np.sum(ref)) * 100.0 if np.sum(ref) > 0 else 0.0

    # f2 — similarity factor
    mean_sq_diff = np.sum((ref - test) ** 2) / n
    f2 = 50.0 * np.log10(100.0 / np.sqrt(1.0 + mean_sq_diff))

    return f1, f2
