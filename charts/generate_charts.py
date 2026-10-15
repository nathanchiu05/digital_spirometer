"""Generate the example tracking charts used in the README.

The data is simulated (seeded, so it's reproducible) to show what the device's
logs look like for a patient who's on track vs one who should be flagged.
Writes a static .svg (for the README) and an interactive .html for each chart.

Run: pip install -r charts/requirements.txt && python3 charts/generate_charts.py
"""
import math
import os
import random

import plotly.graph_objects as go

OUT = os.path.dirname(os.path.abspath(__file__))

# Palette / chrome (light surface)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = "#2a78d6"
CRITICAL = "#d03b3b"
GOOD = "#0ca30c"
FONT = "-apple-system, Segoe UI, Helvetica, Arial, sans-serif"

W, H = 720, 380
DAYS = 21
DAY_AXIS = list(range(1, DAYS + 1))


def fmt(v):
    return f"{int(round(v)):,}"


def base_figure(title, subtitle, ymax, dtick):
    fig = go.Figure()
    fig.update_layout(
        width=W, height=H,
        margin=dict(l=64, r=28, t=78, b=50),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=11, color=MUTED),
        title=dict(
            text=f"<b>{title}</b><br><span style='font-size:12.5px;color:{INK_2}'>{subtitle}</span>",
            x=0, xref="paper", y=0.95, yanchor="top", font=dict(size=17, color=INK),
        ),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, color=INK)),
    )
    fig.update_xaxes(
        title=dict(text="Recovery day", font=dict(size=11.5, color=INK_2)),
        range=[0.5, DAYS + 0.5], tickvals=[1, 5, 10, 15, 20],
        showgrid=False, showline=True, linecolor=AXIS, ticks="", fixedrange=True,
    )
    fig.update_yaxes(
        range=[0, ymax], dtick=dtick, tickformat=",",
        gridcolor=GRID, zeroline=False, fixedrange=True, ticklabelstandoff=8,
    )
    return fig


def goal_line(fig, v, label):
    fig.add_hline(
        y=v, line=dict(color=INK_2, width=1.5, dash="dash"),
        annotation=dict(text=f"<b>{label}</b>", font=dict(size=11.5, color=INK_2), bgcolor=SURFACE, xshift=6),
        annotation_position="top left",
    )


def status_note(fig, x, glyph_color, glyph, label):
    """Status cue: colored icon + text label in ink, pinned to the top of the plot."""
    fig.add_annotation(
        x=x, y=1, xref="x", yref="paper", xanchor="left", yanchor="top", yshift=-6, showarrow=False,
        text=f"<span style='color:{glyph_color}'>{glyph}</span> <b>{label}</b>",
        font=dict(size=12, color=INK),
    )


def flag_band(fig, d0, d1, label):
    fig.add_vrect(x0=d0 - 0.5, x1=d1 + 0.5, fillcolor=CRITICAL, opacity=0.07, line_width=0, layer="below")
    status_note(fig, d0 - 0.3, CRITICAL, "⚠", label)


def save(fig, name):
    fig.write_image(os.path.join(OUT, f"{name}.svg"))
    fig.write_html(os.path.join(OUT, f"{name}.html"), include_plotlyjs="cdn",
                   config={"displayModeBar": False})
    print("wrote", name)


# ---------- Adherence: breaths completed per day vs daily goal ----------
GOAL_BREATHS = 10


def adherence_chart(name, title, subtitle, counts, flag=None):
    fig = base_figure(title, subtitle, 15, 5)
    if flag:
        flag_band(fig, *flag)
    fig.add_bar(
        x=DAY_AXIS, y=counts, marker_color=SERIES, width=0.62,
        hovertemplate="Day %{x}: %{y} breaths<extra></extra>",
    )
    fig.update_layout(barcornerradius=4)
    for d, n in zip(DAY_AXIS, counts):
        if n == 0:
            fig.add_annotation(x=d, y=0, yanchor="bottom", text="0", showarrow=False,
                               font=dict(size=10.5, color=MUTED))
    goal_line(fig, GOAL_BREATHS, f"Daily goal: {GOAL_BREATHS} breaths")
    save(fig, name)


good_adherence = [7, 8, 9, 10, 10, 11, 10, 9, 10, 12, 10, 10, 11, 10, 9, 10, 10, 11, 10, 10, 10]
bad_adherence = [8, 9, 7, 6, 5, 6, 4, 3, 0, 4, 2, 3, 0, 0, 2, 1, 0, 3, 0, 1, 0]
hit = sum(n >= GOAL_BREATHS for n in good_adherence)
low_start = next(d for d, n in enumerate(bad_adherence, 1) if n < GOAL_BREATHS / 2 and
                 all(m < GOAL_BREATHS / 2 for m in bad_adherence[d - 1:]))

adherence_chart("adherence_good", "Adherence: on track",
                f"Breaths completed per day (simulated). Goal met on {hit} of {DAYS} days.",
                good_adherence)
adherence_chart("adherence_bad", "Adherence: falling off",
                f"Breaths completed per day (simulated). Goal met on 0 of {DAYS} days.",
                bad_adherence,
                flag=(low_start, DAYS, f"Under half the goal for {DAYS - low_start + 1} straight days"))


# ---------- Inspiratory capacity: best breath per day vs volume goal ----------
GOAL_ML = 2500
SENSOR_FLOOR_ML = 500
random.seed(7)
improving = [1200 + 1500 * (1 - math.exp(-d / 8)) + random.uniform(-90, 90) for d in DAY_AXIS]
flat = [1350 + random.uniform(-110, 110) - 4 * d for d in DAY_AXIS]


def ic_chart(name, title, subtitle, vals, flag=None, goal_day=None):
    fig = base_figure(title, subtitle, 3000, 500)
    fig.add_hrect(
        y0=0, y1=SENSOR_FLOOR_ML, fillcolor=MUTED, opacity=0.16, line_width=0, layer="below",
        annotation=dict(text=f"Below sensor range (&lt;{SENSOR_FLOOR_ML} mL)", font=dict(size=11, color=INK_2),
                        xshift=6, yshift=4),
        annotation_position="bottom left",
    )
    if flag:
        flag_band(fig, *flag)
    goal_line(fig, GOAL_ML, f"Volume goal: {fmt(GOAL_ML)} mL")
    fig.add_scatter(
        x=DAY_AXIS, y=vals, mode="lines+markers",
        line=dict(color=SERIES, width=2),
        marker=dict(color=SERIES, size=8, line=dict(color=SURFACE, width=2)),
        hovertemplate="Day %{x}: %{y:,.0f} mL<extra></extra>",
    )
    fig.add_annotation(x=DAYS, y=vals[-1], xanchor="right", yanchor="bottom", yshift=8, showarrow=False,
                       text=f"<b>{fmt(vals[-1])} mL</b>", font=dict(size=11.5, color=INK))
    if goal_day:
        status_note(fig, 0.7, GOOD, "✔", f"Goal first reached on day {goal_day}")
    save(fig, name)


first_hit = next(d for d, v in enumerate(improving, 1) if v >= GOAL_ML)
ic_chart("ic_improving", "Inspiratory capacity: improving",
         f"Best breath per day (simulated). Up {fmt(improving[-1] - improving[0])} mL over the program.",
         improving, goal_day=first_hit)
ic_chart("ic_stagnant", "Inspiratory capacity: no improvement",
         f"Best breath per day (simulated). Stuck near {fmt(sum(flat) / DAYS)} mL, well short of the goal.",
         flat, flag=(DAYS - 6, DAYS, "No gain in 7 days"))
