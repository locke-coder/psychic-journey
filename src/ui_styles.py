"""D03 Streamlit CSS tokens and display helpers."""

from __future__ import annotations

from typing import Any


def get_global_styles() -> str:
    """Return the D03 operations-cockpit CSS layer."""
    return """
    <style>
    :root {
        --status-under: #b45309;
        --status-on: #2563eb;
        --status-over: #047857;
        --surface-card: #ffffff;
        --surface-hero: #eef6f4;
        --line-soft: #d7e0ea;
        --text-main: #172033;
        --text-muted: #667085;
    }

    .month-close-hero {
        border: 1px solid var(--line-soft);
        background: linear-gradient(180deg, var(--surface-hero), #ffffff);
        border-radius: 8px;
        padding: 18px;
        margin: 0 0 14px;
        color: var(--text-main);
    }

    .month-close-hero__head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 14px;
    }

    .month-close-hero__eyebrow,
    .excel-freshness-badge__label,
    .security-warning-block__label {
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
    }

    .month-close-hero h1 {
        margin: 2px 0 4px !important;
        font-size: 22px !important;
        line-height: 1.18 !important;
    }

    .month-close-hero p {
        margin: 0;
        color: var(--text-muted) !important;
        font-size: 13px;
    }

    .month-close-hero__grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 8px;
    }

    .month-close-hero__item,
    .excel-freshness-badge,
    .security-warning-block {
        border: 1px solid var(--line-soft);
        border-radius: 8px;
        background: var(--surface-card);
        padding: 10px 12px;
    }

    .month-close-hero__item span {
        display: block;
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 760;
        margin-bottom: 4px;
    }

    .month-close-hero__item strong {
        display: block;
        color: var(--text-main);
        font-size: 14px;
        line-height: 1.28;
        overflow-wrap: anywhere;
    }

    .strategy-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border: 1px solid var(--line-soft);
        border-radius: 999px;
        padding: 5px 9px;
        background: #ffffff;
        color: var(--text-main);
        font-size: 12px;
        font-weight: 800;
        line-height: 1;
        white-space: nowrap;
    }

    .strategy-badge--under {
        border-color: rgba(180, 83, 9, .3);
        color: var(--status-under);
    }

    .strategy-badge--on {
        border-color: rgba(37, 99, 235, .28);
        color: var(--status-on);
    }

    .strategy-badge--over {
        border-color: rgba(4, 120, 87, .28);
        color: var(--status-over);
    }

    .scenario-operation-note {
        border-left: 4px solid var(--status-on);
        background: #f8fafc;
        padding: 10px 12px;
        margin: 8px 0 10px;
        border-radius: 8px;
        color: var(--text-main);
        font-size: 13px;
    }

    .forecast-strategy-board {
        border: 1px solid var(--line-soft);
        border-radius: 8px;
        background: #f8fafc;
        padding: 16px 18px;
        margin: 0 0 12px;
    }

    .forecast-strategy-board__eyebrow {
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
    }

    .forecast-strategy-board h2 {
        margin: 3px 0 5px !important;
        color: var(--text-main);
        font-size: 22px !important;
        line-height: 1.2 !important;
    }

    .forecast-strategy-board p {
        margin: 0;
        color: var(--text-muted);
        font-size: 13px;
        line-height: 1.5;
    }

    .unified-decision-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 8px;
        margin: 0 0 14px;
    }

    .unified-decision-strip__item {
        border: 1px solid var(--line-soft);
        border-radius: 8px;
        background: var(--surface-card);
        padding: 11px 12px;
        min-height: 94px;
    }

    .unified-decision-strip__item span,
    .unified-decision-strip__item small {
        display: block;
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 760;
        line-height: 1.35;
    }

    .unified-decision-strip__item strong {
        display: block;
        margin: 5px 0 4px;
        color: var(--text-main);
        font-size: 15px;
        line-height: 1.25;
        overflow-wrap: anywhere;
    }

    .unified-model-grid,
    .unified-scenario-panel,
    .unified-detail-expander {
        border: 1px solid var(--line-soft);
        border-radius: 8px;
        background: var(--surface-card);
    }

    .strategy-recommendation-pulse .unified-decision-strip__item:nth-child(7) {
        border-color: rgba(37, 99, 235, .34);
        background: #eff6ff;
    }

    .excel-freshness-badge {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin: 8px 0 12px;
    }

    .excel-freshness-badge strong {
        color: var(--text-main);
        font-size: 14px;
    }

    .security-warning-block {
        margin: 10px 0 12px;
        border-color: rgba(180, 83, 9, .36);
        background: #fffbeb;
    }

    .security-warning-block strong {
        display: block;
        margin-top: 4px;
        color: #92400e;
        font-size: 13px;
        line-height: 1.45;
    }

    div[data-testid="stDataFrame"] {
        overflow-x: auto;
    }

    @media (max-width: 900px) {
        .month-close-hero__grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .month-close-hero__head,
        .excel-freshness-badge {
            flex-direction: column;
            align-items: stretch;
        }

        .unified-decision-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 620px) {
        .month-close-hero__grid {
            grid-template-columns: 1fr;
        }

        .unified-decision-strip {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """


def inject_global_styles(st_module: Any | None = None) -> None:
    """Inject D03 styles into Streamlit."""
    if st_module is None:
        import streamlit as st_module

    st_module.markdown(get_global_styles(), unsafe_allow_html=True)
