"""
Shared plotting utilities using Plotly for interactive Streamlit figures.

Consistent color palette and styling across all pages.

All data is synthetic/hypothetical for educational purposes only.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

# =============================================================================
# Color Palette
# =============================================================================

COLORS = {
    'F1 (Fast)': '#2196F3',      # Blue
    'F2 (Medium)': '#FF9800',    # Orange
    'F3 (Slow)': '#4CAF50',      # Green
    'IR Reference': '#9E9E9E',   # Gray

    'A (Low MW)': '#2196F3',
    'B (Medium MW)': '#FF9800',
    'C (High MW)': '#4CAF50',
    'Solution': '#9E9E9E',

    'P1': '#E91E63',             # Pink (pathological)
    'P2': '#9C27B0',             # Purple (pathological)

    'primary': '#2196F3',
    'success': '#4CAF50',
    'warning': '#FF9800',
    'danger': '#F44336',
    'info': '#00BCD4',
    'muted': '#9E9E9E',
}

LAYOUT_DEFAULTS = dict(
    font=dict(family='Arial, sans-serif', size=13),
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin=dict(l=60, r=30, t=50, b=50),
    legend=dict(
        bgcolor='rgba(255,255,255,0.9)',
        bordercolor='#ddd',
        borderwidth=1,
    ),
)


def _base_layout(**kwargs):
    """Merge default layout with custom kwargs."""
    layout = {**LAYOUT_DEFAULTS}
    layout.update(kwargs)
    return layout


# =============================================================================
# Level A Plots
# =============================================================================

def plot_dissolution_profiles(times, profiles, ir_profile=None,
                              title='In Vitro Dissolution Profiles',
                              x_label='Time (h)', y_label='Cumulative % Released'):
    """Plot dissolution curves for multiple formulations."""
    fig = go.Figure()

    for name, release in profiles.items():
        color = COLORS.get(name, '#666')
        fig.add_trace(go.Scatter(
            x=times, y=release,
            mode='lines+markers',
            name=name,
            line=dict(color=color, width=2.5),
            marker=dict(size=6),
        ))

    if ir_profile is not None:
        fig.add_trace(go.Scatter(
            x=times, y=ir_profile,
            mode='lines+markers',
            name='IR Reference',
            line=dict(color=COLORS['IR Reference'], width=2, dash='dash'),
            marker=dict(size=5, symbol='diamond'),
        ))

    fig.update_layout(
        **_base_layout(title=title),
        xaxis=dict(title=x_label, gridcolor='#eee', zeroline=False),
        yaxis=dict(title=y_label, gridcolor='#eee', range=[0, 105], zeroline=False),
    )
    return fig


def plot_pk_profiles(times, profiles, title='Plasma Concentration-Time Profiles',
                     x_label='Time (h)', y_label='Concentration (mg/L)',
                     ir_pk=None):
    """Plot PK curves for multiple formulations."""
    fig = go.Figure()

    for name, conc in profiles.items():
        color = COLORS.get(name, '#666')
        fig.add_trace(go.Scatter(
            x=times, y=conc,
            mode='lines+markers',
            name=name,
            line=dict(color=color, width=2.5),
            marker=dict(size=6),
        ))

    if ir_pk is not None:
        fig.add_trace(go.Scatter(
            x=times, y=ir_pk,
            mode='lines+markers',
            name='IR Reference',
            line=dict(color=COLORS['IR Reference'], width=2, dash='dash'),
            marker=dict(size=5, symbol='diamond'),
        ))

    fig.update_layout(
        **_base_layout(title=title),
        xaxis=dict(title=x_label, gridcolor='#eee', zeroline=False),
        yaxis=dict(title=y_label, gridcolor='#eee', zeroline=False),
    )
    return fig


def plot_absorption_vs_dissolution(times_diss, dissolution, times_abs, absorption,
                                    name='Formulation',
                                    color='#2196F3'):
    """Overlay in vitro dissolution vs in vivo fraction absorbed."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=times_diss, y=dissolution,
        mode='lines+markers',
        name='% Dissolved (in vitro)',
        line=dict(color=color, width=2.5),
        marker=dict(size=6),
    ))

    fig.add_trace(go.Scatter(
        x=times_abs, y=absorption * 100,
        mode='lines+markers',
        name='% Absorbed (in vivo)',
        line=dict(color=color, width=2.5, dash='dash'),
        marker=dict(size=6, symbol='x'),
    ))

    fig.update_layout(
        **_base_layout(title=f'{name}: Dissolution vs Absorption'),
        xaxis=dict(title='Time (h)', gridcolor='#eee', zeroline=False),
        yaxis=dict(title='%', gridcolor='#eee', range=[0, 105], zeroline=False),
    )
    return fig


def plot_level_a_correlation(all_dissolved, all_absorbed, slope, intercept,
                              r_squared, title='Level A Correlation'):
    """Scatter plot of % dissolved vs % absorbed with regression line."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=all_dissolved, y=all_absorbed,
        mode='markers',
        name='Data',
        marker=dict(size=8, color=COLORS['primary'], opacity=0.7),
    ))

    # Regression line
    x_fit = np.linspace(0, 100, 100)
    y_fit = slope * x_fit + intercept
    fig.add_trace(go.Scatter(
        x=x_fit, y=y_fit,
        mode='lines',
        name=f'y = {slope:.3f}x + {intercept:.2f}',
        line=dict(color=COLORS['danger'], width=2),
    ))

    # 1:1 line
    fig.add_trace(go.Scatter(
        x=[0, 100], y=[0, 100],
        mode='lines',
        name='1:1 Line (ideal)',
        line=dict(color='#ccc', width=1.5, dash='dot'),
    ))

    fig.update_layout(
        **_base_layout(title=f'{title} (R² = {r_squared:.4f})'),
        xaxis=dict(title='% Dissolved (in vitro)', gridcolor='#eee',
                   range=[0, 105], zeroline=False),
        yaxis=dict(title='% Absorbed (in vivo)', gridcolor='#eee',
                   range=[0, 105], zeroline=False),
    )
    return fig


def plot_pe_validation(formulation_names, pe_cmax, pe_auc):
    """Bar chart of %PE for each formulation (Cmax and AUC)."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=['Cmax %PE', 'AUC %PE'])

    # Cmax
    colors_cmax = [COLORS['success'] if abs(v) <= 15 else COLORS['danger']
                   for v in pe_cmax]
    fig.add_trace(go.Bar(
        x=formulation_names, y=pe_cmax,
        marker_color=colors_cmax,
        name='Cmax %PE',
        showlegend=False,
    ), row=1, col=1)

    # AUC
    colors_auc = [COLORS['success'] if abs(v) <= 15 else COLORS['danger']
                  for v in pe_auc]
    fig.add_trace(go.Bar(
        x=formulation_names, y=pe_auc,
        marker_color=colors_auc,
        name='AUC %PE',
        showlegend=False,
    ), row=1, col=2)

    # Threshold lines
    for col in [1, 2]:
        fig.add_hline(y=15, line_dash='dash', line_color='red',
                      annotation_text='±15%', row=1, col=col)
        fig.add_hline(y=-15, line_dash='dash', line_color='red', row=1, col=col)
        fig.add_hline(y=10, line_dash='dot', line_color='orange',
                      annotation_text='±10% (mean)', row=1, col=col)
        fig.add_hline(y=-10, line_dash='dot', line_color='orange', row=1, col=col)

    fig.update_layout(**_base_layout(title='Internal Validation: %Prediction Error'))
    return fig


# =============================================================================
# Level B Plots
# =============================================================================

def plot_mdt_vs_mrt(formulation_names, mdt_values, mrt_values):
    """Scatter plot of MDT vs MRT for Level B."""
    fig = go.Figure()

    for name in formulation_names:
        color = COLORS.get(name, '#666')
        fig.add_trace(go.Scatter(
            x=[mdt_values[name]],
            y=[mrt_values[name]],
            mode='markers+text',
            name=name,
            text=[name],
            textposition='top center',
            marker=dict(size=14, color=color),
        ))

    # Regression line
    x_vals = np.array([mdt_values[n] for n in formulation_names])
    y_vals = np.array([mrt_values[n] for n in formulation_names])

    if len(x_vals) >= 2:
        from scipy import stats
        slope, intercept, r, p, se = stats.linregress(x_vals, y_vals)
        x_fit = np.linspace(x_vals.min() * 0.8, x_vals.max() * 1.2, 50)
        y_fit = slope * x_fit + intercept
        fig.add_trace(go.Scatter(
            x=x_fit, y=y_fit,
            mode='lines',
            name=f'R² = {r**2:.3f}',
            line=dict(color='gray', dash='dash', width=1.5),
        ))

    fig.update_layout(
        **_base_layout(title='Level B: MDT vs MRT'),
        xaxis=dict(title='MDT — Mean Dissolution Time (h)', gridcolor='#eee', zeroline=False),
        yaxis=dict(title='MRT — Mean Residence Time (h)', gridcolor='#eee', zeroline=False),
    )
    return fig


def plot_pathological_example(data):
    """Show two formulations with same MDT but different profiles."""
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Dissolution Profiles', 'PK Profiles'])

    # Dissolution
    fig.add_trace(go.Scatter(
        x=data['times'], y=data['P1_dissolution'],
        name=f"P1 (biphasic, MDT={data['MDT_P1']:.1f}h)",
        line=dict(color=COLORS['P1'], width=2.5),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data['times'], y=data['P2_dissolution'],
        name=f"P2 (steady, MDT={data['MDT_P2']:.1f}h)",
        line=dict(color=COLORS['P2'], width=2.5),
    ), row=1, col=1)

    # PK
    fig.add_trace(go.Scatter(
        x=data['times'], y=data['P1_pk'],
        name=f"P1 (MRT={data['MRT_P1']:.1f}h)",
        line=dict(color=COLORS['P1'], width=2.5, dash='dash'),
        showlegend=False,
    ), row=1, col=2)

    fig.add_trace(go.Scatter(
        x=data['times'], y=data['P2_pk'],
        name=f"P2 (MRT={data['MRT_P2']:.1f}h)",
        line=dict(color=COLORS['P2'], width=2.5, dash='dash'),
        showlegend=False,
    ), row=1, col=2)

    fig.update_xaxes(title_text='Time (h)', gridcolor='#eee', row=1, col=1)
    fig.update_xaxes(title_text='Time (h)', gridcolor='#eee', row=1, col=2)
    fig.update_yaxes(title_text='% Released', gridcolor='#eee', row=1, col=1)
    fig.update_yaxes(title_text='Concentration (mg/L)', gridcolor='#eee', row=1, col=2)

    fig.update_layout(
        **_base_layout(title='Limitation: Same MDT ≠ Same PK'),
        height=400,
    )
    return fig


# =============================================================================
# Level C Plots
# =============================================================================

def plot_level_c_scatter(in_vitro, in_vivo, iv_name, vivo_name,
                          formulation_names, slope, intercept, r_squared):
    """Level C scatter plot for one parameter pair."""
    fig = go.Figure()

    for i, name in enumerate(formulation_names):
        color = COLORS.get(name, '#666')
        fig.add_trace(go.Scatter(
            x=[in_vitro[i]], y=[in_vivo[i]],
            mode='markers+text',
            name=name,
            text=[name.split(' ')[0]],
            textposition='top center',
            marker=dict(size=14, color=color),
        ))

    # Regression
    x_range = np.linspace(min(in_vitro) * 0.8, max(in_vitro) * 1.2, 50)
    y_fit = slope * x_range + intercept
    fig.add_trace(go.Scatter(
        x=x_range, y=y_fit,
        mode='lines',
        name=f'Fit (R²={r_squared:.3f})',
        line=dict(color='gray', dash='dash', width=1.5),
    ))

    slope_dir = '↑' if slope > 0 else '↓'
    fig.update_layout(
        **_base_layout(title=f'{iv_name} vs {vivo_name} — R²={r_squared:.3f} {slope_dir}'),
        xaxis=dict(title=iv_name, gridcolor='#eee', zeroline=False),
        yaxis=dict(title=vivo_name, gridcolor='#eee', zeroline=False),
        showlegend=True,
    )
    return fig


def plot_correlation_heatmap(r2_matrix, iv_names, vivo_names, slope_matrix):
    """Interactive R² heatmap for Level C correlation matrix."""
    # Annotations with R² value + slope arrow
    annotations = []
    for i in range(len(iv_names)):
        for j in range(len(vivo_names)):
            arrow = '↑' if slope_matrix[i, j] > 0 else '↓'
            annotations.append(f"{r2_matrix[i, j]:.2f} {arrow}")

    text_matrix = np.array(annotations).reshape(len(iv_names), len(vivo_names))

    fig = go.Figure(data=go.Heatmap(
        z=r2_matrix,
        x=vivo_names,
        y=iv_names,
        text=text_matrix,
        texttemplate='%{text}',
        colorscale='Blues',
        zmin=0, zmax=1,
        colorbar=dict(title='R²'),
    ))

    fig.update_layout(
        **_base_layout(title='Level C Correlation Matrix (R² + Slope Direction)'),
        xaxis=dict(title='In Vivo Parameter', side='bottom'),
        yaxis=dict(title='In Vitro Parameter', autorange='reversed'),
        height=500,
    )
    return fig


def plot_f1_f2_bars(f1_f2_results):
    """f1/f2 bar chart with regulatory thresholds."""
    pairs = list(f1_f2_results.keys())
    f1_vals = [f1_f2_results[p]['f1'] for p in pairs]
    f2_vals = [f1_f2_results[p]['f2'] for p in pairs]

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['f1 (Difference Factor)', 'f2 (Similarity Factor)'])

    # f1 bars
    f1_colors = [COLORS['success'] if v <= 15 else COLORS['danger'] for v in f1_vals]
    fig.add_trace(go.Bar(x=pairs, y=f1_vals, marker_color=f1_colors,
                         name='f1', showlegend=False), row=1, col=1)
    fig.add_hline(y=15, line_dash='dash', line_color='red',
                  annotation_text='f1 ≤ 15 (Similar)', row=1, col=1)

    # f2 bars
    f2_colors = [COLORS['success'] if v >= 50 else COLORS['danger'] for v in f2_vals]
    fig.add_trace(go.Bar(x=pairs, y=f2_vals, marker_color=f2_colors,
                         name='f2', showlegend=False), row=1, col=2)
    fig.add_hline(y=50, line_dash='dash', line_color='green',
                  annotation_text='f2 ≥ 50 (Similar)', row=1, col=2)

    fig.update_layout(
        **_base_layout(title='f1/f2 Dissolution Similarity Analysis'),
        height=400,
    )
    return fig
