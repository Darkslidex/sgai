"""
Gráficos reutilizables — Tema luxury oscuro con paleta dorada.

Todos los gráficos usan Plotly con:
- Fondo transparente / negro
- Paleta: Gold → Ivory → Muted → Success → Alert
- Grilla sutil dorada
- Tipografía Inter
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ── Paleta ───────────────────────────────────────────────────────────────────

GOLD       = "#C9A84C"
GOLD_LIGHT = "#E8C96A"
GOLD_MUTED = "#8A6F2E"
IVORY      = "#F2E8D5"
TAN        = "#A89B7A"
MUTED      = "#6B5F47"
SUCCESS    = "#5A9E6F"
DANGER     = "#A86060"
SILVER     = "#C0B8A8"
BLUE       = "#7BA8C4"

COLORWAY = [GOLD, IVORY, SILVER, SUCCESS, BLUE, DANGER, GOLD_MUTED, TAN]

GRID_COLOR = "rgba(201,168,76,0.07)"
ZERO_COLOR = "rgba(201,168,76,0.15)"

# ── Base layout ──────────────────────────────────────────────────────────────

def _base_layout(title: str = "", height: int = 340) -> dict:
    return dict(
        title=dict(
            text=title,
            font=dict(family="Playfair Display, serif", size=15, color=IVORY),
            x=0, xanchor="left", pad=dict(l=0, b=16),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,20,0.6)",
        font=dict(family="Inter, sans-serif", color=TAN, size=11),
        colorway=COLORWAY,
        height=height,
        margin=dict(l=0, r=10, t=48 if title else 10, b=0),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=MUTED, size=10),
            bordercolor=GRID_COLOR,
        ),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickfont=dict(color=MUTED, size=10),
            linecolor=GRID_COLOR,
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickfont=dict(color=MUTED, size=10),
            linecolor=GRID_COLOR,
        ),
    )


# ── Chart Functions ───────────────────────────────────────────────────────────

def line_chart(
    df: pd.DataFrame,
    x: str,
    y: str | list[str],
    title: str = "",
    color: str = GOLD,
    target_line: float | None = None,
    height: int = 320,
) -> go.Figure:
    """Gráfico de línea con área sombreada suave."""
    fig = go.Figure()
    ys = [y] if isinstance(y, str) else y
    colors = [GOLD, IVORY, SILVER, SUCCESS]

    for i, col in enumerate(ys):
        c = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col],
            mode="lines+markers",
            name=col,
            line=dict(color=c, width=2),
            marker=dict(size=4, color=c, symbol="circle"),
            fill="tozeroy",
            fillcolor=f"rgba{_hex_to_rgba(c, 0.05)}",
        ))

    if target_line is not None:
        fig.add_hline(
            y=target_line,
            line_dash="dash",
            line_color=GOLD_MUTED,
            line_width=1,
            annotation_text="objetivo",
            annotation_font=dict(color=GOLD_MUTED, size=10),
        )

    fig.update_layout(**_base_layout(title, height))
    return fig


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: str = GOLD,
    horizontal: bool = False,
    height: int = 320,
) -> go.Figure:
    """Gráfico de barras elegante."""
    if horizontal:
        fig = go.Figure(go.Bar(
            y=df[x], x=df[y],
            orientation="h",
            marker=dict(
                color=COLORWAY[:len(df)],
                line=dict(color="rgba(0,0,0,0)", width=0),
            ),
        ))
    else:
        fig = go.Figure(go.Bar(
            x=df[x], y=df[y],
            marker=dict(
                color=color,
                opacity=0.85,
                line=dict(color="rgba(0,0,0,0)", width=0),
            ),
        ))

    fig.update_layout(**_base_layout(title, height))
    return fig


def multi_bar_chart(
    df: pd.DataFrame,
    x: str,
    ys: list[str],
    title: str = "",
    height: int = 320,
) -> go.Figure:
    """Gráfico de barras agrupadas."""
    colors = [GOLD, IVORY, SUCCESS, SILVER]
    fig = go.Figure()
    for i, col in enumerate(ys):
        fig.add_trace(go.Bar(
            x=df[x], y=df[col],
            name=col,
            marker=dict(color=colors[i % len(colors)], opacity=0.85),
        ))
    fig.update_layout(**_base_layout(title, height), barmode="group")
    return fig


def donut_chart(
    labels: list[str],
    values: list[float],
    title: str = "",
    height: int = 300,
) -> go.Figure:
    """Gráfico de dona — para distribuciones por categoría."""
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        marker=dict(
            colors=COLORWAY[:len(labels)],
            line=dict(color="#080808", width=2),
        ),
        textinfo="label+percent",
        textfont=dict(color=IVORY, size=10),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}<br>%{percent}<extra></extra>",
    ))

    layout = _base_layout(title, height)
    layout.update(
        showlegend=True,
        legend=dict(
            orientation="v",
            x=1, y=0.5,
            font=dict(color=TAN, size=10),
        ),
    )
    fig.update_layout(**layout)
    return fig


def heatmap(
    df: pd.DataFrame,
    title: str = "",
    height: int = 320,
) -> go.Figure:
    """Heatmap — para correlaciones o actividad semanal."""
    fig = go.Figure(go.Heatmap(
        z=df.values,
        x=df.columns.tolist(),
        y=df.index.tolist(),
        colorscale=[
            [0.0, "#141414"],
            [0.3, GOLD_MUTED],
            [0.7, GOLD],
            [1.0, GOLD_LIGHT],
        ],
        hoverongaps=False,
        showscale=True,
        colorbar=dict(
            tickfont=dict(color=MUTED),
            outlinecolor=GRID_COLOR,
            thickness=10,
        ),
    ))

    layout = _base_layout(title, height)
    layout["xaxis"].update(tickangle=0)
    fig.update_layout(**layout)
    return fig


def scatter_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color_col: str | None = None,
    size_col: str | None = None,
    height: int = 320,
) -> go.Figure:
    """Scatter plot para correlaciones."""
    kwargs = dict(
        x=df[x], y=df[y],
        mode="markers",
        marker=dict(
            color=GOLD if color_col is None else df[color_col],
            colorscale=[[0, GOLD_MUTED], [1, GOLD_LIGHT]] if color_col else None,
            size=8 if size_col is None else df[size_col].clip(5, 20),
            opacity=0.8,
            line=dict(color="rgba(0,0,0,0.3)", width=1),
        ),
        text=df.index if hasattr(df, "index") else None,
        hovertemplate=f"<b>{x}</b>: %{{x}}<br><b>{y}</b>: %{{y}}<extra></extra>",
    )
    fig = go.Figure(go.Scatter(**kwargs))
    fig.update_layout(**_base_layout(title, height))
    return fig


def gauge_chart(
    value: float,
    max_val: float,
    title: str = "",
    unit: str = "",
    height: int = 220,
) -> go.Figure:
    """Gauge/velocímetro para métricas individuales."""
    pct = min(value / max_val, 1.0) if max_val > 0 else 0

    color = DANGER if pct < 0.4 else (GOLD if pct < 0.8 else SUCCESS)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=title, font=dict(family="Playfair Display, serif", color=IVORY, size=13)),
        number=dict(suffix=unit, font=dict(family="Playfair Display, serif", color=IVORY, size=28)),
        gauge=dict(
            axis=dict(range=[0, max_val], tickcolor=MUTED, tickfont=dict(color=MUTED, size=9)),
            bar=dict(color=color, thickness=0.25),
            bgcolor="rgba(30,30,30,0.8)",
            borderwidth=1,
            bordercolor=GRID_COLOR,
            steps=[
                dict(range=[0, max_val * 0.4], color="rgba(168,96,96,0.15)"),
                dict(range=[max_val * 0.4, max_val * 0.8], color="rgba(201,168,76,0.08)"),
                dict(range=[max_val * 0.8, max_val], color="rgba(90,158,111,0.12)"),
            ],
        ),
    ))

    layout = _base_layout("", height)
    del layout["xaxis"], layout["yaxis"]
    layout["margin"] = dict(l=20, r=20, t=30, b=10)
    fig.update_layout(**layout)
    return fig


# ── Util ─────────────────────────────────────────────────────────────────────

def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convierte #RRGGBB a (R,G,B,A) para uso en rgba()."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"({r},{g},{b},{alpha})"
