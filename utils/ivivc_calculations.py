"""
IVIVC correlation calculations for Levels A, B, and C.

Includes %PE validation, linear regression, and correlation analysis.

All data is synthetic/hypothetical for educational purposes only.
"""

import numpy as np
from scipy import stats


def level_a_correlation(dissolved_fractions, absorbed_fractions):
    """
    Level A IVIVC: Point-to-point correlation between
    % dissolved and % absorbed at matched timepoints.

    Parameters
    ----------
    dissolved_fractions : list of array-like
        In vitro % dissolved for each formulation (list of arrays).
    absorbed_fractions : list of array-like
        In vivo % absorbed for each formulation (list of arrays).

    Returns
    -------
    dict
        'slope', 'intercept', 'r_squared', 'p_value', 'std_err',
        'all_dissolved', 'all_absorbed' (pooled data arrays)
    """
    all_dissolved = []
    all_absorbed = []

    for diss, abso in zip(dissolved_fractions, absorbed_fractions):
        diss = np.asarray(diss, dtype=float)
        abso = np.asarray(abso, dtype=float)
        # Use minimum length if mismatched
        n = min(len(diss), len(abso))
        all_dissolved.extend(diss[:n])
        all_absorbed.extend(abso[:n])

    all_dissolved = np.array(all_dissolved)
    all_absorbed = np.array(all_absorbed)

    if len(all_dissolved) < 2:
        return {
            'slope': 0, 'intercept': 0, 'r_squared': 0,
            'p_value': 1.0, 'std_err': 0,
            'all_dissolved': all_dissolved,
            'all_absorbed': all_absorbed,
        }

    slope, intercept, r_value, p_value, std_err = stats.linregress(
        all_dissolved, all_absorbed
    )

    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_value ** 2,
        'p_value': p_value,
        'std_err': std_err,
        'all_dissolved': all_dissolved,
        'all_absorbed': all_absorbed,
    }


def level_c_correlation(in_vitro_values, in_vivo_values):
    """
    Level C IVIVC: Single-point correlation between one
    dissolution parameter and one PK parameter.

    Parameters
    ----------
    in_vitro_values : array-like
        One in vitro parameter per formulation (e.g., [DE_A, DE_B, DE_C]).
    in_vivo_values : array-like
        One in vivo parameter per formulation (e.g., [AUC_A, AUC_B, AUC_C]).

    Returns
    -------
    dict
        'slope', 'intercept', 'r_squared', 'p_value', 'std_err',
        'in_vitro', 'in_vivo' (original arrays)
    """
    x = np.asarray(in_vitro_values, dtype=float)
    y = np.asarray(in_vivo_values, dtype=float)

    if len(x) < 2:
        return {
            'slope': 0, 'intercept': 0, 'r_squared': 0,
            'p_value': 1.0, 'std_err': 0,
            'in_vitro': x, 'in_vivo': y,
        }

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_value ** 2,
        'p_value': p_value,
        'std_err': std_err,
        'in_vitro': x,
        'in_vivo': y,
    }


def compute_prediction_error(predicted, observed):
    """
    Compute %PE (Prediction Error) for IVIVC validation.

    %PE = (Predicted - Observed) / Observed × 100

    FDA criteria:
    - Mean |%PE| ≤ 10% for Cmax and AUC
    - Individual |%PE| ≤ 15%

    Parameters
    ----------
    predicted : float or array-like
        Predicted PK parameter(s).
    observed : float or array-like
        Observed PK parameter(s).

    Returns
    -------
    dict
        'pe_values': individual %PE values,
        'abs_pe': absolute %PE values,
        'mean_abs_pe': mean |%PE|,
        'max_abs_pe': max |%PE|,
        'passes_mean': bool (mean ≤ 10%),
        'passes_individual': bool (all ≤ 15%),
        'passes_overall': bool (both criteria met)
    """
    predicted = np.atleast_1d(np.asarray(predicted, dtype=float))
    observed = np.atleast_1d(np.asarray(observed, dtype=float))

    # Avoid division by zero
    mask = observed != 0
    pe = np.zeros_like(predicted)
    pe[mask] = ((predicted[mask] - observed[mask]) / observed[mask]) * 100.0

    abs_pe = np.abs(pe)
    mean_abs_pe = float(np.mean(abs_pe))
    max_abs_pe = float(np.max(abs_pe)) if len(abs_pe) > 0 else 0.0

    return {
        'pe_values': pe,
        'abs_pe': abs_pe,
        'mean_abs_pe': mean_abs_pe,
        'max_abs_pe': max_abs_pe,
        'passes_mean': mean_abs_pe <= 10.0,
        'passes_individual': max_abs_pe <= 15.0,
        'passes_overall': mean_abs_pe <= 10.0 and max_abs_pe <= 15.0,
    }


def build_correlation_matrix(in_vitro_params, in_vivo_params,
                              iv_names, vivo_names):
    """
    Build full Level C correlation matrix (R² and slope for all pairs).

    Parameters
    ----------
    in_vitro_params : dict
        {param_name: [val_A, val_B, val_C]} for each in vitro parameter.
    in_vivo_params : dict
        {param_name: [val_A, val_B, val_C]} for each in vivo parameter.
    iv_names : list of str
        Ordered in vitro parameter names.
    vivo_names : list of str
        Ordered in vivo parameter names.

    Returns
    -------
    dict
        'r_squared_matrix': 2D array (n_iv × n_vivo),
        'slope_matrix': 2D array,
        'p_value_matrix': 2D array,
        'iv_names': list, 'vivo_names': list
    """
    n_iv = len(iv_names)
    n_vivo = len(vivo_names)

    r2_matrix = np.zeros((n_iv, n_vivo))
    slope_matrix = np.zeros((n_iv, n_vivo))
    p_matrix = np.zeros((n_iv, n_vivo))

    for i, iv_name in enumerate(iv_names):
        for j, vivo_name in enumerate(vivo_names):
            result = level_c_correlation(
                in_vitro_params[iv_name],
                in_vivo_params[vivo_name]
            )
            r2_matrix[i, j] = result['r_squared']
            slope_matrix[i, j] = result['slope']
            p_matrix[i, j] = result['p_value']

    return {
        'r_squared_matrix': r2_matrix,
        'slope_matrix': slope_matrix,
        'p_value_matrix': p_matrix,
        'iv_names': iv_names,
        'vivo_names': vivo_names,
    }
