"""
Synthetic data generation for all IVIVC levels.

Generates completely hypothetical data from mathematical models
for educational/demonstration purposes only.
No real experimental data is used.
"""

import numpy as np
from .dissolution_models import (
    first_order_release, weibull_release,
    compute_mdt, compute_de, compute_f1_f2
)
from .pk_models import (
    one_compartment_oral, impulse_response_1comp,
    convolve_dissolution_pk, biexponential_depot,
    compute_auc, compute_mrt
)
from .deconvolution import wagner_nelson


# =============================================================================
# Level A — Extended-Release Oral Tablet Scenario
# =============================================================================

def generate_level_a_data(k_fast=0.30, k_medium=0.15, k_slow=0.08):
    """
    Generate synthetic Level A data: 3 ER oral formulations + IR reference.

    Drug: "Compound Y" — BCS Class II, 1-compartment PK
    - ke = 0.10 h⁻¹ (elimination)
    - Vd = 50 L
    - Dose = 100 mg

    Parameters
    ----------
    k_fast : float
        Dissolution rate constant for fast formulation (h⁻¹).
    k_medium : float
        Dissolution rate constant for medium formulation (h⁻¹).
    k_slow : float
        Dissolution rate constant for slow formulation (h⁻¹).

    Returns
    -------
    dict with keys:
        'times_dissolution', 'times_pk', 'times_fine',
        'dissolution_profiles', 'pk_profiles',
        'fraction_absorbed', 'ir_dissolution', 'ir_pk',
        'pk_params', 'dissolution_params', 'ke'
    """
    # PK parameters
    ke = 0.10   # h⁻¹
    vd = 50.0   # L
    dose = 100.0  # mg

    # Time vectors
    times_diss = np.array([0, 0.25, 0.5, 1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24])
    times_pk = np.array([0, 0.5, 1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24])
    times_fine = np.linspace(0, 24, 500)  # For smooth curves

    # Dissolution rates
    k_values = {'F1 (Fast)': k_fast, 'F2 (Medium)': k_medium, 'F3 (Slow)': k_slow}
    formulation_names = ['F1 (Fast)', 'F2 (Medium)', 'F3 (Slow)']

    dissolution_profiles = {}
    dissolution_profiles_fine = {}
    pk_profiles = {}
    pk_profiles_fine = {}
    fraction_absorbed = {}
    pk_params = {}
    dissolution_params = {}

    for name in formulation_names:
        k = k_values[name]

        # Dissolution
        diss = first_order_release(times_diss, k, f_max=100.0)
        diss_fine = first_order_release(times_fine, k, f_max=100.0)
        dissolution_profiles[name] = diss
        dissolution_profiles_fine[name] = diss_fine

        # PK via analytical 1-compartment oral model
        # ka = k (dissolution-rate limited, so absorption rate ≈ dissolution rate)
        ka = k * 1.5  # absorption slightly faster than dissolution
        pk = one_compartment_oral(times_pk, dose, ka, ke, vd)
        pk_fine = one_compartment_oral(times_fine, dose, ka, ke, vd)
        pk_profiles[name] = pk
        pk_profiles_fine[name] = pk_fine

        # Wagner-Nelson deconvolution
        wn = wagner_nelson(times_pk, pk, ke)
        fraction_absorbed[name] = wn

        # PK parameters
        cmax = float(np.max(pk))
        tmax = float(times_pk[np.argmax(pk)])
        auc = compute_auc(times_pk, pk)
        mrt = compute_mrt(times_pk, pk)

        pk_params[name] = {
            'Cmax': cmax,
            'Tmax': tmax,
            'AUC': auc,
            'MRT': mrt,
        }

        # Dissolution parameters
        mdt = compute_mdt(times_diss, diss)
        de = compute_de(times_diss, diss)
        t50 = np.log(2) / k if k > 0 else np.inf

        dissolution_params[name] = {
            'MDT': mdt,
            'DE': de,
            't50': t50,
            'k': k,
        }

    # IR reference
    ir_diss = first_order_release(times_diss, k=5.0, f_max=100.0)  # Very fast
    ir_diss_fine = first_order_release(times_fine, k=5.0, f_max=100.0)
    ir_pk = one_compartment_oral(times_pk, dose, ka=5.0, ke=ke, vd=vd)
    ir_pk_fine = one_compartment_oral(times_fine, dose, ka=5.0, ke=ke, vd=vd)

    return {
        'times_dissolution': times_diss,
        'times_pk': times_pk,
        'times_fine': times_fine,
        'dissolution_profiles': dissolution_profiles,
        'dissolution_profiles_fine': dissolution_profiles_fine,
        'pk_profiles': pk_profiles,
        'pk_profiles_fine': pk_profiles_fine,
        'fraction_absorbed': fraction_absorbed,
        'ir_dissolution': ir_diss,
        'ir_dissolution_fine': ir_diss_fine,
        'ir_pk': ir_pk,
        'ir_pk_fine': ir_pk_fine,
        'pk_params': pk_params,
        'dissolution_params': dissolution_params,
        'ke': ke,
        'vd': vd,
        'dose': dose,
        'formulation_names': formulation_names,
    }


# =============================================================================
# Level B — Statistical Moment Comparison
# =============================================================================

def generate_level_b_data(k_fast=0.30, k_medium=0.15, k_slow=0.08,
                          p1_burst_frac=40.0, p1_burst_k=2.0,
                          p2_k=0.16):
    """
    Generate Level B data (MDT vs MRT) from Level A scenario,
    plus a pathological example showing limitation of Level B.

    Parameters
    ----------
    k_fast, k_medium, k_slow : float
        Dissolution rate constants for the 3 ER formulations (h⁻¹).
    p1_burst_frac : float
        Fraction of dose in burst phase for pathological P1 (%).
    p1_burst_k : float
        Burst phase rate constant for P1 (h⁻¹).
    p2_k : float
        First-order dissolution rate constant for P2 (h⁻¹).

    Returns
    -------
    dict with keys:
        'formulation_names', 'mdt_values', 'mrt_values',
        'pathological_example' (two formulations with same MDT, different PK)
    """
    # Get Level A data for standard comparison
    data_a = generate_level_a_data(k_fast=k_fast, k_medium=k_medium,
                                    k_slow=k_slow)

    mdt_values = {}
    mrt_values = {}
    vdt_values = {}  # Variance of dissolution time

    for name in data_a['formulation_names']:
        mdt_values[name] = data_a['dissolution_params'][name]['MDT']
        mrt_values[name] = data_a['pk_params'][name]['MRT']

        # VDT calculation
        times = data_a['times_dissolution']
        diss = data_a['dissolution_profiles'][name]
        delta_f = np.diff(diss)
        t_mid = (times[:-1] + times[1:]) / 2.0
        mdt = mdt_values[name]
        total_df = np.sum(delta_f)
        if total_df > 0:
            vdt = np.sum((t_mid - mdt) ** 2 * delta_f) / total_df
        else:
            vdt = 0
        vdt_values[name] = vdt

    # Pathological example: two formulations with same MDT but different profiles
    times_path = np.linspace(0, 24, 100)

    # Formulation P1: Biphasic — fast burst then slow (MDT ≈ 4.5h)
    p1_slow_frac = 100.0 - p1_burst_frac
    p1_release = p1_burst_frac * (1 - np.exp(-p1_burst_k * times_path)) + \
                 p1_slow_frac * (1 - np.exp(-0.05 * times_path))
    p1_release = np.minimum(p1_release, 100)

    # Formulation P2: Zero-order-like — steady release (MDT ≈ 4.5h)
    p2_release = first_order_release(times_path, k=p2_k, f_max=100.0)

    # Compute MDTs to verify they're similar
    mdt_p1 = compute_mdt(times_path, p1_release)
    mdt_p2 = compute_mdt(times_path, p2_release)

    # Generate PK for both
    ke = 0.10
    vd = 50.0
    dose = 100.0
    p1_pk = one_compartment_oral(times_path, dose, ka=0.8, ke=ke, vd=vd)
    p2_pk = one_compartment_oral(times_path, dose, ka=0.25, ke=ke, vd=vd)

    mrt_p1 = compute_mrt(times_path, p1_pk)
    mrt_p2 = compute_mrt(times_path, p2_pk)

    return {
        'formulation_names': data_a['formulation_names'],
        'mdt_values': mdt_values,
        'mrt_values': mrt_values,
        'vdt_values': vdt_values,
        'level_a_data': data_a,
        'pathological': {
            'times': times_path,
            'P1_dissolution': p1_release,
            'P2_dissolution': p2_release,
            'P1_pk': p1_pk,
            'P2_pk': p2_pk,
            'MDT_P1': mdt_p1,
            'MDT_P2': mdt_p2,
            'MRT_P1': mrt_p1,
            'MRT_P2': mrt_p2,
        },
    }


# =============================================================================
# Level C — PLGA Depot Scenario (matches ivivc-level-c-viz architecture)
# =============================================================================

def generate_level_c_data(
    # Formulation A Weibull params
    fmax_A=88, tau_A=300, beta_A=0.75, burst_A=15, burst_tau_A=8,
    # Formulation B Weibull params
    fmax_B=68, tau_B=420, beta_B=0.70, burst_B=7, burst_tau_B=10,
    # Formulation C Weibull params
    fmax_C=58, tau_C=500, beta_C=0.68, burst_C=4.5, burst_tau_C=11,
    # PK params: (a1, alpha1, ka, a2, alpha2) per formulation
    pk_A_params=(0.90, 0.004, 1.2, 0.08, 0.0006),
    pk_B_params=(0.60, 0.0025, 0.20, 0.20, 0.0005),
    pk_C_params=(0.25, 0.0012, 0.06, 0.35, 0.0003),
):
    """
    Generate synthetic Level C IVIVC data for PLGA depot formulations.

    Scenario: Hypothetical PLGA microsphere depot (IM injection)
    - Formulation A (Low MW PLGA): Fast degradation, high burst
    - Formulation B (Medium MW PLGA): Moderate release
    - Formulation C (High MW PLGA): Slow release

    Returns
    -------
    dict with all data needed for Level C tutorial
    """
    # Time vectors (hours)
    iv_times_h = np.array([0, 1, 6, 24, 72, 168, 336, 504, 672, 720])
    iv_times_d = iv_times_h / 24.0

    pk_times_h = np.array([0.5, 1, 2, 4, 6, 8, 12, 24, 48, 72, 168, 336, 504, 672, 840])
    pk_times_d = pk_times_h / 24.0

    # In vitro release profiles (Weibull model)
    release_A = weibull_release(iv_times_h, fmax=fmax_A, tau=tau_A, beta=beta_A,
                                burst_frac=burst_A, burst_tau=burst_tau_A)
    release_B = weibull_release(iv_times_h, fmax=fmax_B, tau=tau_B, beta=beta_B,
                                burst_frac=burst_B, burst_tau=burst_tau_B)
    release_C = weibull_release(iv_times_h, fmax=fmax_C, tau=tau_C, beta=beta_C,
                                burst_frac=burst_C, burst_tau=burst_tau_C)
    release_sol = np.minimum(100, 100 * (1 - np.exp(-0.5 * iv_times_h)))

    # PK profiles (bi-exponential depot)
    pk_A = biexponential_depot(pk_times_h, *pk_A_params)
    pk_B = biexponential_depot(pk_times_h, *pk_B_params)
    pk_C = biexponential_depot(pk_times_h, *pk_C_params)

    # Normalize to C/Cmax of A
    cmax_A = np.max(pk_A)
    pk_A_norm = pk_A / cmax_A
    pk_B_norm = pk_B / cmax_A
    pk_C_norm = pk_C / cmax_A

    formulations = ['A (Low MW)', 'B (Medium MW)', 'C (High MW)']

    # Derive in vitro parameters
    def get_release_at(times, release, target_h):
        idx = np.argmin(np.abs(times - target_h))
        return float(release[idx])

    iv_params = {}
    for name, rel in zip(formulations, [release_A, release_B, release_C]):
        mdt = compute_mdt(iv_times_h, rel)
        de = compute_de(iv_times_h, rel)
        iv_params[name] = {
            '%Rel 1h': get_release_at(iv_times_h, rel, 1),
            '%Rel 6h': get_release_at(iv_times_h, rel, 6),
            '%Rel 24h': get_release_at(iv_times_h, rel, 24),
            '%Rel 72h': get_release_at(iv_times_h, rel, 72),
            '%Rel 7d': get_release_at(iv_times_h, rel, 168),
            '%Rel 14d': get_release_at(iv_times_h, rel, 336),
            'MDT (h)': mdt,
            'DE (%)': de,
        }

    # Derive in vivo parameters
    vivo_params = {}
    for name, pk_norm, pk_raw in zip(
        formulations,
        [pk_A_norm, pk_B_norm, pk_C_norm],
        [pk_A, pk_B, pk_C]
    ):
        auc = compute_auc(pk_times_h, pk_norm)
        mrt = compute_mrt(pk_times_h, pk_norm)
        tmax = float(pk_times_h[np.argmax(pk_norm)])

        vivo_params[name] = {
            'AUC_norm': auc,
            'MRT (h)': mrt,
            'Tmax (h)': tmax,
        }

    # f1/f2 analysis
    f1_f2_results = {}
    pairs = [('A (Low MW)', 'B (Medium MW)'),
             ('A (Low MW)', 'C (High MW)'),
             ('B (Medium MW)', 'C (High MW)')]
    release_map = {'A (Low MW)': release_A, 'B (Medium MW)': release_B,
                   'C (High MW)': release_C}
    for ref_name, test_name in pairs:
        f1, f2 = compute_f1_f2(release_map[ref_name], release_map[test_name])
        label = f"{ref_name.split(' ')[0]} vs {test_name.split(' ')[0]}"
        f1_f2_results[label] = {'f1': f1, 'f2': f2}

    # Also vs solution
    for name in formulations:
        f1, f2 = compute_f1_f2(release_map[name], release_sol)
        label = f"{name.split(' ')[0]} vs Solution"
        f1_f2_results[label] = {'f1': f1, 'f2': f2}

    return {
        'iv_times_h': iv_times_h,
        'iv_times_d': iv_times_d,
        'pk_times_h': pk_times_h,
        'pk_times_d': pk_times_d,
        'dissolution': {
            'A (Low MW)': release_A,
            'B (Medium MW)': release_B,
            'C (High MW)': release_C,
            'Solution': release_sol,
        },
        'pk_normalized': {
            'A (Low MW)': pk_A_norm,
            'B (Medium MW)': pk_B_norm,
            'C (High MW)': pk_C_norm,
        },
        'formulations': formulations,
        'iv_params': iv_params,
        'vivo_params': vivo_params,
        'f1_f2': f1_f2_results,
    }
