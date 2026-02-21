"""
Pharmacokinetic models for synthetic in vivo data generation.

All data is synthetic/hypothetical for educational purposes only.
"""

import numpy as np

# NumPy 2.0 removed np.trapz → np.trapezoid
_trapz = getattr(np, 'trapezoid', None) or np.trapz


def one_compartment_oral(t, dose, ka, ke, vd):
    """
    One-compartment oral PK model (first-order absorption + elimination).

    C(t) = (dose * ka) / (vd * (ka - ke)) * [exp(-ke*t) - exp(-ka*t)]

    Parameters
    ----------
    t : array-like
        Time points (hours).
    dose : float
        Dose (mg).
    ka : float
        Absorption rate constant (h⁻¹).
    ke : float
        Elimination rate constant (h⁻¹).
    vd : float
        Volume of distribution (L).

    Returns
    -------
    np.ndarray
        Plasma concentration at each time point.
    """
    t = np.asarray(t, dtype=float)
    if abs(ka - ke) < 1e-10:
        # Limiting case: ka ≈ ke
        return (dose / vd) * ka * t * np.exp(-ke * t)

    coeff = (dose * ka) / (vd * (ka - ke))
    return coeff * (np.exp(-ke * t) - np.exp(-ka * t))


def impulse_response_1comp(t, ke, vd):
    """
    Unit impulse response for 1-compartment model (IV bolus).

    h(t) = (1/vd) * exp(-ke * t)

    Parameters
    ----------
    t : array-like
        Time points (hours).
    ke : float
        Elimination rate constant (h⁻¹).
    vd : float
        Volume of distribution (L).

    Returns
    -------
    np.ndarray
        Impulse response at each time point.
    """
    t = np.asarray(t, dtype=float)
    return (1.0 / vd) * np.exp(-ke * t)


def convolve_dissolution_pk(times, dissolution_rate, impulse_resp):
    """
    Numerical convolution of dissolution rate with PK impulse response.

    C(t) = ∫₀ᵗ r(τ) · h(t-τ) dτ

    Parameters
    ----------
    times : array-like
        Evenly-spaced time points (hours).
    dissolution_rate : array-like
        In vitro dissolution rate (dF/dt, fraction/hour).
    impulse_resp : array-like
        PK impulse response h(t).

    Returns
    -------
    np.ndarray
        Predicted plasma concentration profile.
    """
    times = np.asarray(times, dtype=float)
    dt = times[1] - times[0] if len(times) > 1 else 1.0

    # Full convolution, take only first N points
    conv = np.convolve(dissolution_rate, impulse_resp) * dt
    return conv[:len(times)]


def biexponential_depot(t, a1, alpha1, ka, a2, alpha2):
    """
    Bi-exponential depot PK model for long-acting injectables.

    C(t) = A1·exp(-α1·t)·(1-exp(-ka·t)) + A2·exp(-α2·t)

    Parameters
    ----------
    t : array-like
        Time points (hours).
    a1 : float
        Coefficient for absorption-elimination phase.
    alpha1 : float
        Disposition rate constant (h⁻¹).
    ka : float
        Absorption rate constant (h⁻¹).
    a2 : float
        Coefficient for sustained phase.
    alpha2 : float
        Terminal elimination rate constant (h⁻¹).

    Returns
    -------
    np.ndarray
        Plasma concentration at each time point.
    """
    t = np.asarray(t, dtype=float)
    return a1 * np.exp(-alpha1 * t) * (1.0 - np.exp(-ka * t)) + a2 * np.exp(-alpha2 * t)


def compute_auc(times, conc):
    """
    Compute AUC using trapezoidal rule.

    Parameters
    ----------
    times : array-like
        Time points.
    conc : array-like
        Concentration values.

    Returns
    -------
    float
        Area under the curve.
    """
    return float(_trapz(conc, times))


def compute_aumc(times, conc):
    """
    Compute AUMC (Area Under the Moment Curve).

    AUMC = ∫ t·C(t) dt

    Parameters
    ----------
    times : array-like
        Time points.
    conc : array-like
        Concentration values.

    Returns
    -------
    float
        Area under the first moment curve.
    """
    times = np.asarray(times, dtype=float)
    conc = np.asarray(conc, dtype=float)
    return float(_trapz(times * conc, times))


def compute_mrt(times, conc):
    """
    Compute Mean Residence Time.

    MRT = AUMC / AUC

    Parameters
    ----------
    times : array-like
        Time points.
    conc : array-like
        Concentration values.

    Returns
    -------
    float
        Mean residence time.
    """
    auc = compute_auc(times, conc)
    aumc = compute_aumc(times, conc)

    if auc == 0:
        return 0.0

    return aumc / auc
