"""D03 Streamlit CSS tokens and display helpers."""

from __future__ import annotations

from typing import Any


def get_global_styles() -> str:
    """Return the D03 operations-cockpit CSS layer."""
    return """
    <style>
    :root,
    .stApp {
        --status-under: #db3707;
        --status-on: #1d4aff;
        --status-over: #12806d;
        --surface-card: #ffffff;
        --surface-hero: #fff8df;
        --surface-alt: #f3f4ef;
        --line-soft: #d0d1c9;
        --line-strong: #b6b6ad;
        --text-main: #1d1f27;
        --text-muted: #5f5e5b;
        --brand-action: #1d4aff;
        --brand-personality: #f9bd2b;
    }

    .month-close-hero {
        border: 1px solid var(--line-soft);
        border-top: 4px solid var(--brand-personality);
        background: linear-gradient(180deg, var(--surface-hero), var(--surface-card) 48%);
        border-radius: 6px;
        padding: 18px 20px 20px;
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
        border-radius: 6px;
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
        border-radius: 6px;
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
        border-left: 4px solid var(--brand-action);
        border-radius: 6px;
        background: var(--surface-alt);
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
        border-radius: 6px;
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
        border-color: var(--brand-action);
        background: #eef1ff;
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

    section[data-testid="stSidebar"] button[kind="primary"] {
        background: var(--brand-action) !important;
        border-color: var(--brand-action) !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] button[kind="primary"] p {
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] button[kind="secondary"] {
        background: var(--surface-card) !important;
        border-color: var(--line-soft) !important;
        border-radius: 6px !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] button[kind="secondary"]:hover {
        border-color: var(--line-strong) !important;
        background: var(--surface-alt) !important;
    }

    /* Navy + royal-blue dashboard theme, aligned to the approved reference. */
    :root,
    .stApp {
        --status-under: #dc4a43;
        --status-on: #2f65e8;
        --status-over: #19866f;
        --surface-card: #ffffff;
        --surface-hero: #ffffff;
        --surface-alt: #f3f6fb;
        --line-soft: #dfe5ef;
        --line-strong: #c8d1e0;
        --text-main: #14213d;
        --text-muted: #6f7a8c;
        --brand-action: #2f65e8;
        --brand-personality: #2f65e8;
        --dashboard-navy: #17213d;
        --dashboard-blue-soft: #eaf0ff;
        --chart-bg: #ffffff;
        --app-bg: #f3f6fb;
        --surface: #ffffff;
        --surface-muted: #f6f8fc;
        --surface-soft: #eef3ff;
        --accent: #2f65e8;
        --accent-soft: #eaf0ff;
        --teal: #2f65e8;
        --teal-soft: #eaf0ff;
        --amber: #6f8fe8;
        --slate: #65738b;
        --bg: #f3f6fb;
        --ink: #14213d;
        --ink-2: #6f7a8c;
        --muted: #7f899a;
        --line: #dfe5ef;
        --surface-2: #f6f8fc;
        --radius-lg: 10px;
        --radius-md: 8px;
    }

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: #f3f6fb !important;
    }

    .block-container {
        max-width: 1460px !important;
        padding-top: 1.5rem !important;
    }

    .month-close-hero {
        margin: 0 0 12px;
        padding: 0;
        border: 0;
        border-radius: 0;
        background: transparent;
    }

    .month-close-hero__head {
        display: none;
    }

    .month-close-hero__grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
    }

    .month-close-hero__item {
        padding: 15px 18px;
        border-radius: 10px;
        box-shadow: 0 1px 2px rgba(20, 33, 61, .04);
    }

    .month-close-hero__item strong {
        font-size: 22px;
        font-weight: 800;
    }

    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div {
        background: var(--dashboard-navy) !important;
    }

    section[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"] {
        border: 1px solid rgba(255, 255, 255, .28) !important;
        border-radius: 7px !important;
        background: rgba(255, 255, 255, .12) !important;
        color: #ffffff !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, .18) !important;
    }

    section[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"]:hover {
        border-color: #7fa4ff !important;
        background: var(--brand-action) !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"] span {
        color: inherit !important;
    }

    section[data-testid="stSidebar"] .nav-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 2px 16px;
        color: #ffffff;
    }

    .nav-brand__mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        flex: 0 0 28px;
        border-radius: 8px;
        background: var(--brand-action);
        color: #ffffff;
        font-size: 14px;
        font-weight: 900;
    }

    .nav-brand strong,
    .nav-brand small {
        display: block;
    }

    .nav-brand strong {
        font-size: 15px;
        line-height: 1.2;
    }

    .nav-brand small {
        margin-top: 2px;
        color: #8fa0c4;
        font-size: 10px;
        letter-spacing: .04em;
    }

    section[data-testid="stSidebar"] .same-window-nav-group,
    section[data-testid="stSidebar"] .security-warning-block__label {
        border-bottom-color: rgba(255, 255, 255, .1) !important;
        color: #8293b8 !important;
    }

    .security-warning-block {
        border-color: rgba(255, 255, 255, .1);
        background: rgba(255, 255, 255, .06);
    }

    .security-warning-block strong {
        color: #c8d2e8;
    }

    section[data-testid="stSidebar"] button[kind="secondary"] {
        border-color: transparent !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: #c8d2e8 !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] button[kind="secondary"] p {
        color: #c8d2e8 !important;
    }

    section[data-testid="stSidebar"] button[kind="secondary"]:hover {
        border-color: rgba(255, 255, 255, .08) !important;
        background: rgba(255, 255, 255, .08) !important;
    }

    .same-window-top-status {
        grid-template-columns: minmax(180px, auto) minmax(0, 1fr) !important;
        margin: 8px 0 18px !important;
        padding: 14px 18px !important;
        border-radius: 10px !important;
        background: #ffffff !important;
        box-shadow: 0 1px 2px rgba(20, 33, 61, .04) !important;
    }

    .same-window-top-status__brand {
        display: none !important;
    }

    .same-window-top-status__page {
        font-size: 20px !important;
        font-weight: 800 !important;
    }

    .same-window-top-status__meta {
        justify-content: flex-end;
    }

    .pace-pill {
        padding: 7px 11px !important;
        border: 0 !important;
        border-radius: 7px !important;
        background: #f1f4f9 !important;
        color: #53617a !important;
    }

    .pace-pill.is-primary {
        background: var(--brand-action) !important;
        color: #ffffff !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head) {
        grid-template-columns: calc((100% - 24px) / 3) minmax(0, 1fr) !important;
        gap: 12px !important;
        margin-top: 0 !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head)
        > div[data-testid="stColumn"]:has(.home-side-stack)
        > div[data-testid="stVerticalBlock"]
        > div[data-testid="stElementContainer"]:has(.home-side-stack) {
        display: flex !important;
        flex: 1 1 auto !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head)
        div[data-testid="stElementContainer"]:has(.home-side-stack)
        > div[data-testid="stMarkdown"] {
        display: flex !important;
        flex: 1 1 auto !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head)
        div[data-testid="stElementContainer"]:has(.home-side-stack)
        > div[data-testid="stMarkdown"]
        > div {
        align-items: stretch !important;
        flex: 1 1 auto !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head)
        div[data-testid="stMarkdownContainer"]:has(.home-side-stack) {
        flex: 1 1 auto !important;
        height: auto !important;
        margin-bottom: 0 !important;
    }

    .home-side-stack {
        display: flex;
        flex-direction: column;
        gap: 12px;
        width: 100%;
        height: 100%;
    }

    .achievement-card {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 132px;
        align-items: center;
        gap: 16px;
        min-height: 194px;
        padding: 16px 18px;
        border: 1px solid var(--line-soft);
        border-radius: 10px;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(20, 33, 61, .04);
    }

    .achievement-card__copy {
        min-width: 0;
    }

    .achievement-card__eyebrow {
        color: var(--brand-action);
        font-size: 11px;
        font-weight: 800;
        line-height: 1.2;
    }

    .achievement-card h2 {
        margin: 4px 0 6px !important;
        padding: 0 !important;
        border: 0 !important;
        color: var(--text-main) !important;
        font-size: 17px !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        word-break: keep-all !important;
        overflow-wrap: normal !important;
    }

    .achievement-card p {
        margin: 0 0 10px !important;
        color: var(--text-muted) !important;
        font-size: 12px !important;
        line-height: 1.5 !important;
        word-break: keep-all;
    }

    .achievement-card__comparison {
        display: inline-flex;
        padding: 5px 8px;
        border-radius: 6px;
        background: #eef3ff;
        color: var(--brand-action);
        font-size: 12px;
        font-weight: 800;
        line-height: 1.25;
    }

    .achievement-card.is-over .achievement-card__comparison {
        background: #fff1e8;
        color: #d65f16;
    }

    .achievement-donut {
        position: relative;
        display: grid;
        place-items: center;
        width: 132px;
        height: 132px;
        border-radius: 50%;
    }

    .achievement-donut::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 50%;
        background: conic-gradient(#f47a2a 0 var(--excess-angle), transparent var(--excess-angle) 360deg);
        -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px));
        mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px));
        transform: rotate(-90deg);
    }

    .achievement-donut__ring {
        position: absolute;
        inset: 10px;
        border-radius: 50%;
        background: conic-gradient(var(--brand-action) 0 var(--achievement-angle), #e7ecf4 var(--achievement-angle) 360deg);
        transform: rotate(-90deg);
    }

    .achievement-donut__ring::after {
        content: "";
        position: absolute;
        inset: 13px;
        border-radius: 50%;
        background: #ffffff;
        box-shadow: inset 0 0 0 1px rgba(223, 229, 239, .7);
    }

    .achievement-donut__value {
        position: relative;
        z-index: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        color: var(--text-main);
    }

    .achievement-donut__value strong {
        font-size: 23px;
        font-weight: 850;
        line-height: 1.05;
        letter-spacing: -0.03em;
    }

    .achievement-card.is-over .achievement-donut__value strong {
        color: #d65f16;
    }

    .achievement-donut__value span {
        margin-top: 4px;
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 700;
    }

    .home-side-stack .decision-panel {
        flex: 1 1 auto;
        height: auto !important;
        min-height: 0 !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head),
    .decision-panel,
    .projection-chart-card,
    .projection-chart-card__head {
        background: #ffffff !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head),
    .decision-panel {
        border-color: var(--line-soft) !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 2px rgba(20, 33, 61, .04) !important;
    }

    button[kind="primary"],
    div[data-testid="stFormSubmitButton"] button {
        border-color: var(--brand-action) !important;
        background: var(--brand-action) !important;
        color: #ffffff !important;
    }

    button[kind="primary"] p,
    div[data-testid="stFormSubmitButton"] button p {
        color: #ffffff !important;
    }

    /* Shared component language across every routed page. */
    .page-header,
    .pace-mode-card,
    .metric-card,
    .metric-card-compact,
    .kpi-card,
    .scenario-card,
    .strategy-section,
    .report-card,
    .excel-card,
    .next-action-panel,
    .excel-readonly-panel,
    .report-memo-card,
    .history-purpose-card,
    .compact-arrival-chart,
    .unified-model-grid,
    .unified-scenario-panel,
    .unified-detail-expander {
        border-color: var(--line-soft) !important;
        border-radius: 10px !important;
        background: var(--surface-card) !important;
        box-shadow: 0 1px 2px rgba(20, 33, 61, .04) !important;
    }

    .page-header {
        padding: 15px 17px !important;
    }

    .page-header__eyebrow,
    .page-header-compact__eyebrow,
    .decision-panel__label,
    .next-action-panel__label,
    .excel-readonly-panel__label,
    .forecast-strategy-board__eyebrow,
    .unified-model-grid__eyebrow {
        color: var(--brand-action) !important;
    }

    .section-header {
        border-left: 3px solid var(--brand-action) !important;
        padding-left: 12px !important;
    }

    .section-header::before,
    .page-header::before {
        background: var(--brand-action) !important;
    }

    .strategy-section.is-active-management,
    .strategy-card-active.is-recommended .scenario-card,
    .strategy-recommendation-pulse .unified-decision-strip__item:nth-child(7) {
        border-color: #b9caf6 !important;
        background: #f7f9ff !important;
        box-shadow: inset 0 0 0 1px rgba(47, 101, 232, .12) !important;
    }

    .strategy-section__head span,
    .strategy-section .status-badge,
    .strategy-card-shell__badge.is-recommended-badge {
        color: #2457cb !important;
    }

    .strategy-card-shell__badge.is-recommended-badge {
        border-color: #b9caf6 !important;
        background: var(--dashboard-blue-soft) !important;
    }

    div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input,
    div[data-testid="stFileUploaderDropzone"],
    textarea,
    [data-testid="stDataFrame"],
    [data-testid="stDataEditor"] {
        border-color: var(--line-soft) !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        box-shadow: none !important;
    }

    div[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within,
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus,
    textarea:focus {
        border-color: var(--brand-action) !important;
        box-shadow: 0 0 0 2px rgba(47, 101, 232, .12) !important;
    }

    div[data-testid="stExpander"] details {
        overflow: hidden;
        border: 1px solid var(--line-soft) !important;
        border-radius: 8px !important;
        background: #ffffff !important;
    }

    div[data-testid="stExpander"] summary:hover,
    div[data-testid="stFileUploaderDropzone"]:hover {
        background: #f7f9ff !important;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--brand-action) !important;
        border-bottom-color: var(--brand-action) !important;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background: var(--brand-action) !important;
    }

    button[kind="secondary"],
    div[data-testid="stDownloadButton"] button {
        border-color: var(--line-soft) !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        color: var(--text-main) !important;
        box-shadow: none !important;
    }

    button[kind="secondary"]:hover,
    div[data-testid="stDownloadButton"] button:hover {
        border-color: #9db5f1 !important;
        background: #f7f9ff !important;
        color: #2457cb !important;
    }

    div[data-testid="stAlert"] {
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    .chart-legend-row .legend-actual {
        border-color: var(--brand-action) !important;
    }

    .chart-legend-row .legend-projection {
        border-color: #6f8fe8 !important;
    }

    .chart-legend-row .legend-band {
        background: rgba(111, 143, 232, .16) !important;
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

        .same-window-top-status,
        div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head) {
            grid-template-columns: 1fr !important;
        }

        .same-window-top-status__meta {
            justify-content: flex-start;
        }

        .achievement-card {
            grid-template-columns: minmax(0, 1fr) 128px;
        }

        .achievement-donut {
            width: 128px;
            height: 128px;
        }
    }

    @media (max-width: 620px) {
        .month-close-hero__grid {
            grid-template-columns: 1fr;
        }

        .unified-decision-strip {
            grid-template-columns: 1fr;
        }

        .achievement-card {
            grid-template-columns: 1fr;
        }

        .achievement-donut {
            margin: 0 auto;
        }
    }
    </style>
    """


def inject_global_styles(st_module: Any | None = None) -> None:
    """Inject D03 styles into Streamlit."""
    if st_module is None:
        import streamlit as st_module

    st_module.markdown(get_global_styles(), unsafe_allow_html=True)


def get_app_base_styles_css() -> str:
    """Return the base Streamlit app CSS layer."""
    return """
        <style>
        :root {
            --app-bg: #f6f8fb;
            --panel-bg: #ffffff;
            --line-soft: #d9e2ec;
            --line-strong: #b8c6d6;
            --text-main: #18212f;
            --text-muted: #667085;
            --accent: #1f6f78;
            --accent-soft: #e7f3f4;
            --font-title: 1.72rem;
            --font-section: 1.12rem;
            --font-subsection: 0.98rem;
            --font-body: 0.88rem;
            --font-control: 0.86rem;
            --font-caption: 0.78rem;
            --font-small: 0.72rem;
            --font-kpi-value: 1.02rem;
            --metric-card-height: 100px;
            --line-body: 1.48;
            --line-tight: 1.22;
        }

        .stApp {
            background: var(--app-bg);
            color: var(--text-main);
            font-size: var(--font-body);
            line-height: var(--line-body);
        }

        [data-testid="stHeader"] {
            background: rgba(246, 248, 251, 0.92);
            border-bottom: 1px solid rgba(217, 226, 236, 0.72);
        }

        footer {
            display: none !important;
            visibility: hidden !important;
        }

        .block-container {
            max-width: 1480px;
            padding-top: 0.78rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.55rem;
        }

        h1 {
            color: var(--text-main);
            font-size: var(--font-title) !important;
            font-weight: 720 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
            margin-bottom: 1.1rem !important;
        }

        h2 {
            color: var(--text-main);
            font-size: var(--font-section) !important;
            font-weight: 680 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
            margin-top: 1.6rem !important;
            padding-top: 1.05rem !important;
            border-top: 1px solid var(--line-soft);
        }

        h3 {
            color: var(--text-main);
            font-size: var(--font-subsection) !important;
            font-weight: 650 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
            margin-top: 1rem !important;
            margin-bottom: 0.45rem !important;
        }

        p, li, label, div[data-testid="stMarkdownContainer"] {
            color: var(--text-main);
            font-size: var(--font-body) !important;
            line-height: var(--line-body) !important;
            letter-spacing: 0 !important;
        }

        div[data-testid="stCaptionContainer"],
        div[data-testid="stCaptionContainer"] p,
        small {
            color: var(--text-muted) !important;
            font-size: var(--font-caption) !important;
            line-height: 1.38 !important;
            letter-spacing: 0 !important;
        }

        [data-testid="stMetric"] {
            height: var(--metric-card-height);
            min-height: var(--metric-card-height);
            box-sizing: border-box;
            padding: 0.58rem 0.72rem;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            background: var(--panel-bg);
            border: 1px solid var(--line-soft);
            border-left: 3px solid var(--accent);
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] p {
            color: var(--text-muted) !important;
            font-size: var(--font-small) !important;
            font-weight: 620 !important;
            line-height: var(--line-tight) !important;
            margin-bottom: 0.2rem !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--text-main) !important;
            font-size: var(--font-kpi-value) !important;
            font-weight: 700 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
        }

        [data-testid="stMetricDelta"] {
            font-size: var(--font-small) !important;
            line-height: 1.15 !important;
        }

        div[data-testid="stAlert"] {
            border-radius: 8px;
            border: 1px solid var(--line-soft);
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            overflow: hidden;
            background: var(--panel-bg);
        }

        div[data-testid="stDataFrame"] *,
        div[data-testid="stTable"] *,
        [data-testid="stDataEditor"] * {
            font-size: var(--font-control) !important;
            line-height: 1.36 !important;
        }

        div[data-testid="stTabs"] [role="tablist"] {
            gap: 0.2rem;
            border-bottom: 1px solid var(--line-soft);
        }

        button[data-baseweb="tab"] {
            border-radius: 6px 6px 0 0;
            padding: 0.42rem 0.76rem;
            color: var(--text-muted);
            font-size: var(--font-control) !important;
            font-weight: 620;
            line-height: var(--line-tight) !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: var(--accent-soft);
            color: var(--accent);
        }

        div[data-testid="stFileUploader"] section,
        div[data-testid="stExpander"] details {
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            background: var(--panel-bg);
        }

        [data-testid="stFileUploaderDropzone"] button [data-testid="stIconMaterial"],
        [data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] {
            display: none !important;
        }

        [data-testid="stFileUploaderDropzone"] button::after {
            content: "파일 선택";
            font-size: var(--font-control);
            font-weight: 650;
            color: var(--text-main);
        }

        div[data-testid="stExpander"] summary {
            font-size: var(--font-control) !important;
            font-weight: 650;
            color: var(--text-main);
            line-height: var(--line-tight) !important;
        }

        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button {
            border-radius: 6px;
            border: 1px solid var(--line-strong);
            font-size: var(--font-control) !important;
            font-weight: 650;
            line-height: var(--line-tight) !important;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
        }

        div[data-testid="stSelectbox"] label,
        div[data-testid="stDateInput"] label,
        div[data-testid="stNumberInput"] label,
        div[data-testid="stTextInput"] label,
        div[data-testid="stFileUploader"] label {
            font-size: var(--font-control) !important;
            font-weight: 620 !important;
            line-height: var(--line-tight) !important;
        }

        div[data-baseweb="select"] *,
        div[data-baseweb="input"] *,
        div[data-baseweb="base-input"] *,
        div[data-testid="stDateInput"] * {
            font-size: var(--font-control) !important;
            line-height: 1.34 !important;
        }

        textarea,
        input {
            border-radius: 6px !important;
            font-size: var(--font-control) !important;
            line-height: 1.42 !important;
        }

        textarea[aria-label="보고 메모"] {
            font-size: var(--font-body) !important;
            line-height: 1.58 !important;
        }
        .page-header {
            margin: 0 0 8px !important;
            padding: 0 !important;
        }

        .page-header__eyebrow {
            font-size: 11px !important;
            line-height: 1.15 !important;
            margin-bottom: 2px !important;
        }

        .page-header h1 {
            margin: 0 0 5px !important;
            font-size: 25px !important;
            line-height: 1.14 !important;
        }

        .page-header__subtitle {
            font-size: 12px !important;
            line-height: 1.28 !important;
            margin-top: 0 !important;
        }

        .page-header__flow {
            display: flex;
            flex-wrap: wrap;
            gap: 6px 8px;
            margin-top: 9px;
        }

        .page-header__flow-item {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            min-width: 0;
            padding: 5px 8px;
            border: 1px solid var(--line-soft);
            border-radius: 7px;
            background: var(--surface-muted);
            color: var(--text-muted);
            font-size: var(--font-caption) !important;
            line-height: 1.35 !important;
        }

        .page-header__flow-item strong {
            color: var(--text-main);
            font-size: inherit !important;
            white-space: nowrap;
        }

        .page-header__flow-item a,
        .page-header__flow-item a:visited {
            color: var(--teal) !important;
            font-size: inherit !important;
            font-weight: 700;
            text-decoration: none !important;
        }

        .page-header__flow-item a:hover {
            text-decoration: underline !important;
        }

        .workbench-shell,
        .workbench-main {
            color: #25312f;
        }

        .workbench-shell.top-status-bar,
        .page-header-compact {
            border: 1px solid #d8d1c6;
            border-radius: 8px;
            background: #fffdf8;
            padding: 8px 12px;
            margin: 0 0 6px;
            box-shadow: 0 1px 2px rgba(54, 46, 36, 0.06);
        }

        .page-header-compact {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 12px;
            padding: 0;
            margin: 0;
            border: 0;
            box-shadow: none;
        }

        .page-header-compact__eyebrow {
            color: #2f6f68;
            font-size: 11px;
            font-weight: 850;
            line-height: 1.2;
        }

        .page-header-compact h1 {
            margin: 2px 0 0 !important;
            font-size: 19px !important;
            line-height: 1.15 !important;
            font-weight: 850 !important;
            letter-spacing: 0 !important;
        }

        .page-header-compact p {
            margin: 2px 0 0;
            color: #66716e;
            font-size: 12px !important;
            line-height: 1.25 !important;
        }

        .workbench-fact-row {
            display: grid;
            grid-template-columns: repeat(5, minmax(130px, 1fr));
            gap: 8px;
            margin: 8px 0 10px;
        }

        .metric-card-compact {
            min-height: 52px;
            border: 1px solid #d8d1c6;
            border-radius: 8px;
            background: #faf8f3;
            padding: 8px 10px;
        }

        .metric-card-compact span {
            display: block;
            color: #66716e;
            font-size: 11px;
            font-weight: 800;
            line-height: 1.2;
        }

        .metric-card-compact strong {
            display: block;
            margin-top: 3px;
            color: #25312f;
            font-size: 14px;
            font-weight: 850;
            line-height: 1.24;
            overflow-wrap: anywhere;
        }

        .projection-chart-card,
        .decision-panel,
        .report-card,
        .excel-card,
        .empty-state {
            border: 1px solid #d8d1c6;
            border-radius: 8px;
            background: #fffdf8;
            box-shadow: 0 1px 2px rgba(54, 46, 36, 0.06);
        }

        .projection-chart-card {
            padding: 8px 10px 8px;
            min-height: 0;
        }

        .projection-chart-card__head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 4px;
        }

        .projection-chart-card__label {
            color: #25312f;
            font-size: 16px;
            font-weight: 850;
            line-height: 1.25;
        }

        .projection-chart-card__copy {
            margin-top: 2px;
            color: #66716e;
            font-size: 12px;
            line-height: 1.3;
        }

        .chart-legend-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px 12px;
            padding: 8px 2px 0;
            color: #66716e;
            font-size: 12px;
            font-weight: 750;
        }

        .chart-legend-row span {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .chart-legend-row i {
            display: inline-block;
            width: 18px;
            height: 0;
            border-top: 3px solid #2f6f68;
        }

        .chart-legend-row .legend-target {
            border-color: #8a8f98;
            border-top-style: dashed;
        }

        .chart-legend-row .legend-actual {
            border-color: #0f766e;
        }

        .chart-legend-row .legend-projection {
            border-color: #2f6f68;
            border-top-style: dashed;
        }

        .chart-legend-row .legend-band {
            height: 10px;
            border: 0;
            background: #dcebe8;
        }

        .chart-legend-row .legend-close {
            border-color: #b48632;
            border-top-style: dashed;
        }

        .chart-legend-row .legend-current {
            width: 10px;
            height: 10px;
            border: 0;
            border-radius: 999px;
            background: #25312f;
        }

        .decision-panel {
            padding: 10px 12px;
            min-height: 0;
        }

        .decision-panel__label {
            color: #2f6f68;
            font-size: 11px;
            font-weight: 900;
            line-height: 1.2;
            text-transform: uppercase;
        }

        .decision-panel h2 {
            margin: 4px 0 6px !important;
            padding: 0 !important;
            border: 0 !important;
            color: #25312f !important;
            font-size: 17px !important;
            line-height: 1.2 !important;
            font-weight: 850 !important;
        }

        .decision-panel__row {
            display: grid;
            grid-template-columns: 96px 1fr;
            gap: 7px;
            padding: 6px 0;
            border-top: 1px solid #e6ded2;
        }

        .decision-panel__row span {
            color: #66716e;
            font-size: 12px;
            font-weight: 800;
            line-height: 1.3;
        }

        .decision-panel__row strong {
            color: #25312f;
            font-size: 13px;
            font-weight: 800;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }

        .strategy-card-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(220px, 1fr));
            gap: 10px;
            margin: 8px 0 16px;
        }

        .strategy-section,
        .next-action-panel,
        .excel-readonly-panel,
        .compact-arrival-chart {
            border: 1px solid #d8d1c6;
            border-radius: 8px;
            background: #fffdf8;
            box-shadow: 0 1px 2px rgba(54, 46, 36, 0.05);
        }

        .strategy-section {
            padding: 8px;
            margin: 6px 0;
        }

        .strategy-section__head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 8px;
        }

        .strategy-section__status,
        .next-action-panel__label,
        .excel-readonly-panel__label {
            color: #2f6f68;
            font-size: 11px;
            font-weight: 900;
            line-height: 1.2;
            text-transform: uppercase;
        }

        .strategy-section__head p {
            margin: 2px 0 0;
            color: #66716e;
            font-size: 12px !important;
            line-height: 1.32 !important;
        }

        .strategy-section__head span {
            flex: 0 0 auto;
            border: 1px solid #cfd8d5;
            border-radius: 999px;
            background: #eef5f3;
            color: #193b37;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 850;
        }

        .strategy-section__cards {
            display: grid;
            grid-template-columns: repeat(3, minmax(200px, 1fr));
            gap: 7px;
        }

        .strategy-card-shell {
            min-width: 0;
        }

        .strategy-section .scenario-card {
            min-height: 108px;
            border-radius: 8px;
            padding: 8px;
        }

        .strategy-section .scenario-card__topline {
            margin-bottom: 5px;
        }

        .strategy-section .scenario-card__name {
            font-size: 14px;
            line-height: 1.18;
            margin-bottom: 4px;
        }

        .strategy-section .scenario-card__description {
            min-height: 0;
            max-height: 30px;
            overflow: hidden;
            font-size: 11px;
            line-height: 1.32;
        }

        .strategy-section .scenario-card__metrics {
            gap: 6px;
            margin-top: 5px;
        }

        .strategy-section .scenario-card__metric {
            border-radius: 8px;
            padding: 6px;
        }

        .strategy-section .scenario-card__metric-label {
            font-size: 10px;
            margin-bottom: 2px;
        }

        .strategy-section .scenario-card__metric-value {
            font-size: 12px;
            line-height: 1.2;
        }

        .strategy-card-shell__code {
            margin-bottom: 4px;
            color: #53615e;
            font-size: 11px;
            font-weight: 850;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }

        .strategy-card-inactive {
            opacity: 0.72;
        }

        .strategy-card-inactive .scenario-card {
            background: #fbfaf6;
        }

        .compact-arrival-chart {
            padding: 10px;
            margin: 6px 0 8px;
        }

        .scenario-inline-chart-title {
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin: 4px 0 0;
            color: #25312f;
            font-size: 12px;
            line-height: 1.25;
        }

        .scenario-inline-chart-title strong {
            font-size: 13px;
            font-weight: 900;
        }

        .scenario-inline-chart-title span {
            color: #66716e;
            font-size: 11px;
            font-weight: 760;
        }

        .compact-arrival-target {
            margin-bottom: 7px;
            color: #636967;
            font-size: 12px;
            font-weight: 850;
        }

        .compact-arrival-row {
            display: grid;
            grid-template-columns: minmax(136px, 0.28fr) minmax(160px, 1fr) 86px;
            gap: 8px;
            align-items: center;
            padding: 4px 0;
        }

        .compact-arrival-row__label {
            color: #25312f;
            font-size: 12px;
            font-weight: 850;
            line-height: 1.22;
            overflow-wrap: anywhere;
        }

        .compact-arrival-row__label span {
            display: block;
            color: #66716e;
            font-size: 10px;
            font-weight: 760;
        }

        .compact-arrival-row__track {
            height: 14px;
            border-radius: 999px;
            background: #ece6dc;
            overflow: hidden;
        }

        .compact-arrival-row__bar {
            height: 100%;
            border-radius: 999px;
            background: #2f6f68;
        }

        .compact-arrival-row__bar--p {
            background: #b48632;
        }

        .compact-arrival-row__bar--o {
            background: #567c5d;
        }

        .compact-arrival-row__bar--n {
            background: #51758c;
        }

        .compact-arrival-row__bar.is-selected {
            box-shadow: inset 0 0 0 2px rgba(37, 49, 47, 0.34);
        }

        .compact-arrival-row__value {
            color: #25312f;
            font-size: 12px;
            font-weight: 850;
            text-align: right;
        }

        .next-action-panel {
            padding: 10px 12px;
            margin: 10px 0;
        }

        .next-action-panel h3,
        .excel-readonly-panel h3 {
            margin: 3px 0 6px !important;
            padding: 0 !important;
            border: 0 !important;
            color: #25312f !important;
            font-size: 15px !important;
            font-weight: 850 !important;
        }

        .next-action-panel ul {
            margin: 0;
            padding-left: 18px;
        }

        .next-action-panel li {
            margin: 2px 0;
            color: #25312f;
            font-size: 13px !important;
            line-height: 1.38 !important;
        }

        .excel-readonly-panel {
            padding: 10px 12px;
            margin: 8px 0;
        }

        .excel-readonly-panel p {
            margin: 0;
            color: #66716e;
            font-size: 12px !important;
            line-height: 1.38 !important;
        }

        .strategy-card,
        .strategy-card-under,
        .strategy-card-over,
        .strategy-card-neutral {
            border-radius: 8px;
        }

        .strategy-card-under {
            border-color: #d1b98a;
            background: #f6ead4;
        }

        .strategy-card-over {
            border-color: #9fc0a5;
            background: #dfe9de;
        }

        .strategy-card-neutral {
            border-color: #a6b9cb;
            background: #dce6ed;
        }

        section[data-testid="stSidebar"] .nav-rail {
            max-width: 244px;
            padding: 8px;
            border: 1px solid #d8d1c6;
            border-radius: 8px;
            background: #fffdf8;
        }

        section[data-testid="stSidebar"] .nav-rail__title {
            margin: 0 0 8px;
            color: #66716e;
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 0;
        }

        section[data-testid="stSidebar"] .nav-rail a.nav-item,
        section[data-testid="stSidebar"] .nav-rail a.nav-item:visited,
        .mini-nav a.nav-item,
        .mini-nav a.nav-item:visited {
            display: block;
            position: relative;
            margin: 3px 0;
            padding: 8px 10px 8px 12px;
            border: 1px solid transparent;
            border-radius: 8px;
            background: transparent;
            color: #25312f !important;
            text-decoration: none !important;
            box-shadow: none;
        }

        section[data-testid="stSidebar"] .nav-rail a.nav-item:hover,
        .mini-nav a.nav-item:hover {
            border-color: #d2dfdc;
            background: #f3f6f4;
            color: #193b37 !important;
            text-decoration: none !important;
        }

        section[data-testid="stSidebar"] .nav-rail a.nav-item.active,
        .mini-nav a.nav-item.active {
            border-color: #a8c9c3;
            border-left: 4px solid #2f6f68;
            background: #dcebe8;
            color: #193b37 !important;
            font-weight: 850;
            text-decoration: none !important;
        }

        section[data-testid="stSidebar"] .nav-item__label,
        .mini-nav .nav-item__label {
            display: block;
            color: inherit !important;
            font-size: 13px;
            font-weight: 820;
            line-height: 1.25;
            text-decoration: none !important;
        }

        section[data-testid="stSidebar"] .nav-item__marker,
        .mini-nav .nav-item__marker {
            display: inline-block;
            margin-top: 3px;
            color: #2f6f68;
            font-size: 10px;
            font-weight: 900;
            line-height: 1;
        }

        .mini-nav {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 6px 0 8px;
        }

        .mini-nav a.nav-item,
        .mini-nav a.nav-item:visited {
            display: inline-flex !important;
            align-items: center;
            justify-content: center;
            min-height: 30px;
            margin: 0;
            padding: 6px 10px;
            border-radius: 999px;
        }

        .mini-nav .nav-item__label {
            font-size: 12px;
            line-height: 1;
        }

        .mini-nav .nav-item__marker {
            display: none;
        }

        @media (max-width: 1180px) {
            .workbench-fact-row,
            .strategy-card-row,
            .strategy-section__cards {
                grid-template-columns: repeat(2, minmax(180px, 1fr));
            }

            .decision-panel,
            .projection-chart-card {
                min-height: auto;
            }
        }

        @media (max-width: 760px) {
            .workbench-fact-row,
            .strategy-card-row,
            .strategy-section__cards,
            .compact-arrival-row,
            .decision-panel__row {
                grid-template-columns: 1fr;
            }

            .page-header-compact {
                align-items: flex-start;
            }
        }
        </style>
        """


def get_app_layout_styles_css() -> str:
    """Return the page, navigation, and layout CSS layer."""
    return """
        <style>
        :root {
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif;
            --font-app-title: 16px;
            --font-page-title: 20px;
            --font-section-title: 16px;
            --font-card-title: 14px;
            --font-body: 13px;
            --font-body-large: 14px;
            --font-caption: 12px;
            --font-overline: 11px;
            --font-metric-value: 17px;
            --font-nav-title: 13px;
            --font-nav-subtitle: 11px;
            --font-chart-axis: 11px;
            --font-chart-legend: 12px;
            --line-body: 1.62;
            --line-tight: 1.32;
            --line-card: 1.56;
            --app-bg: #f5f7fa;
            --surface: #ffffff;
            --surface-muted: #f7f9fb;
            --surface-soft: #eef6f5;
            --line-soft: #d8e0e7;
            --line-strong: #bcc8d4;
            --text-main: #202833;
            --text-muted: #65717f;
            --teal: #14756f;
            --teal-soft: #e6f3f1;
            --amber: #b7791f;
            --slate: #536170;
            --chart-bg: #f7f9fb;
            --bg: var(--app-bg);
            --ink: var(--text-main);
            --ink-2: var(--text-muted);
            --muted: #7d8793;
            --line: var(--line-soft);
            --surface-2: var(--surface-muted);
            --radius-lg: 8px;
            --radius-md: 8px;
        }

        *,
        *::before,
        *::after {
            box-sizing: border-box;
        }

        html,
        body,
        .stApp,
        .block-container,
        .page-shell,
        .workbench-shell,
        .same-window-top-status,
        .top-status-bar,
        .nav-rail,
        .metric-card,
        .metric-card-compact,
        .decision-panel,
        .report-card,
        .excel-card,
        .projection-chart-card,
        .section-header,
        textarea,
        input,
        button,
        table {
            font-family: var(--font-sans) !important;
        }

        .stApp {
            background: var(--app-bg) !important;
            color: var(--text-main) !important;
            font-size: var(--font-body) !important;
            line-height: var(--line-body) !important;
        }

        .block-container {
            max-width: 1440px;
            padding-top: 2.35rem !important;
            padding-left: clamp(1rem, 2vw, 1.75rem) !important;
            padding-right: clamp(1rem, 2vw, 1.75rem) !important;
            padding-bottom: 3rem !important;
        }

        .page-shell {
            display: block;
            padding-top: 20px;
        }

        [data-testid="stHeader"] {
            background: rgba(245, 247, 250, 0.96) !important;
            border-bottom: 1px solid var(--line-soft) !important;
        }

        h1,
        .page-header h1,
        .pace-hero-title {
            font-family: var(--font-sans) !important;
            font-size: var(--font-page-title) !important;
            font-weight: 700 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
            margin: 0 0 6px !important;
        }

        h2,
        .section-header__title {
            font-size: var(--font-section-title) !important;
            font-weight: 700 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
        }

        h3,
        .projection-chart-card__label,
        .decision-panel h2,
        .next-action-panel h3,
        .excel-readonly-panel h3 {
            font-size: var(--font-card-title) !important;
            font-weight: 700 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
        }

        p,
        li,
        label,
        div[data-testid="stMarkdownContainer"] {
            font-size: var(--font-body) !important;
            font-weight: 400 !important;
            line-height: var(--line-body) !important;
            letter-spacing: 0 !important;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        div[data-testid="stCaptionContainer"],
        div[data-testid="stCaptionContainer"] p,
        small,
        .section-header__subtitle,
        .projection-chart-card__copy,
        .page-header__subtitle {
            color: var(--text-muted) !important;
            font-size: var(--font-caption) !important;
            font-weight: 400 !important;
            line-height: 1.55 !important;
        }

        .page-header {
            display: flow-root;
            min-width: 0;
            margin: 0 0 12px !important;
            padding: 14px 16px 15px !important;
            overflow: hidden;
        }

        .page-header-compact {
            min-width: 0;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden;
        }

        .workbench-shell.top-status-bar {
            margin: 0 0 16px !important;
        }

        .page-header > *:first-child,
        .page-header-compact > *:first-child,
        .section-header > *:first-child,
        .metric-card-compact > *:first-child,
        .kpi-card > *:first-child,
        .scenario-card > *:first-child,
        .report-card > *:first-child,
        .excel-card > *:first-child,
        .next-action-panel > *:first-child,
        .excel-readonly-panel > *:first-child,
        .report-memo-card > *:first-child,
        .history-purpose-card > *:first-child {
            margin-top: 0 !important;
        }

        .page-header > *:last-child,
        .page-header-compact > *:last-child,
        .section-header > *:last-child,
        .metric-card-compact > *:last-child,
        .kpi-card > *:last-child,
        .scenario-card > *:last-child,
        .report-card > *:last-child,
        .excel-card > *:last-child,
        .next-action-panel > *:last-child,
        .excel-readonly-panel > *:last-child,
        .report-memo-card > *:last-child,
        .history-purpose-card > *:last-child {
            margin-bottom: 0 !important;
        }

        .page-header h1 {
            margin: 4px 0 0 !important;
            max-width: 100%;
            overflow-wrap: anywhere;
        }

        .page-header__subtitle {
            margin-top: 7px !important;
            max-width: 100%;
            overflow-wrap: anywhere;
        }

        .page-header__eyebrow,
        .page-header-compact__eyebrow,
        .projection-chart-card__label + .projection-chart-card__copy,
        .decision-panel__label,
        .next-action-panel__label,
        .excel-readonly-panel__label,
        .nav-rail__title {
            letter-spacing: 0.02em !important;
        }

        .page-header__eyebrow,
        .page-header-compact__eyebrow,
        .decision-panel__label,
        .next-action-panel__label,
        .excel-readonly-panel__label,
        .nav-rail__title {
            display: block;
            max-width: 100%;
            color: var(--teal) !important;
            font-size: var(--font-overline) !important;
            font-weight: 700 !important;
            line-height: 1.2 !important;
            text-transform: none;
            overflow-wrap: anywhere;
        }

        .same-window-top-status {
            display: grid;
            grid-template-columns: minmax(180px, 0.7fr) auto minmax(0, 1.3fr);
            align-items: center;
            gap: 12px;
            min-width: 0;
            margin: 22px 0 18px;
            padding: 13px 16px;
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            background: var(--surface);
            box-shadow: 0 1px 2px rgba(28, 39, 49, 0.06);
        }

        .same-window-top-status__brand {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            min-width: 0;
            color: var(--text-main);
            font-size: var(--font-app-title);
            font-weight: 700;
            line-height: 1.35;
        }

        .same-window-top-status__brand span:last-child {
            min-width: 0;
        }

        .same-window-top-status__brand small {
            display: block;
            margin-top: 1px;
            font-size: var(--font-nav-subtitle) !important;
            font-weight: 500;
        }

        .same-window-top-status__page {
            color: var(--text-main);
            font-size: var(--font-card-title);
            font-weight: 700;
            line-height: 1.35;
            min-width: 0;
            white-space: normal;
            overflow-wrap: anywhere;
        }

        .same-window-top-status__meta {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 6px;
            min-width: 0;
        }

        .pace-brand-mark {
            width: 24px !important;
            height: 24px !important;
            border-radius: 7px !important;
            flex: 0 0 auto;
        }

        .pace-pill {
            min-width: 0;
            min-height: 28px;
            padding: 5px 9px;
            border-radius: 999px;
            font-size: var(--font-nav-subtitle) !important;
            font-weight: 500 !important;
            line-height: 1.32 !important;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 220px;
        }

        section[data-testid="stSidebar"] {
            background: var(--surface-muted) !important;
        }

        section[data-testid="stSidebar"] .nav-rail {
            max-width: 100%;
            min-width: 0;
            padding: 4px 0 8px;
            border: 0;
            background: transparent;
        }

        section[data-testid="stSidebar"] .nav-rail__title {
            margin: 0 0 8px;
        }

        section[data-testid="stSidebar"] .same-window-nav-group {
            margin: 13px 2px 4px;
            padding: 0 2px 5px;
            border-bottom: 1px solid var(--line-soft);
            color: var(--text-muted);
            font-size: var(--font-overline) !important;
            font-weight: 800 !important;
            line-height: 1.3 !important;
        }

        section[data-testid="stSidebar"] .same-window-nav-group:first-of-type {
            margin-top: 6px;
        }

        section[data-testid="stSidebar"] div[data-testid="stButton"] button {
            min-width: 0;
            justify-content: flex-start;
            border-radius: 8px;
            padding: 8px 10px;
            font-size: var(--font-nav-title) !important;
            font-weight: 700 !important;
            line-height: 1.42 !important;
            white-space: normal;
            word-break: keep-all;
            overflow-wrap: anywhere;
            text-align: left;
        }

        div[data-testid="stHorizontalBlock"],
        div[data-testid="stHorizontalBlock"] > div,
        div[data-testid="column"],
        div[data-testid="stVerticalBlock"],
        div[data-testid="stVerticalBlock"] > div,
        div[data-testid="stDataFrame"],
        div[data-testid="stTable"],
        div[data-testid="stMetric"],
        .metric-card,
        .metric-card-compact,
        .kpi-grid,
        .kpi-card,
        .decision-panel,
        .report-card,
        .excel-card,
        .nav-item,
        .projection-chart-card,
        .section-header,
        .strategy-section,
        .strategy-section__head,
        .strategy-section__cards,
        .strategy-card-shell,
        .scenario-card,
        .scenario-card__metrics,
        .report-memo-card,
        .history-purpose-card {
            min-width: 0;
        }

        .text-wrap,
        .page-header,
        .page-header-compact,
        .section-header,
        .metric-card,
        .metric-card-compact,
        .decision-panel,
        .report-card,
        .excel-card,
        .projection-chart-card,
        .kpi-card,
        .scenario-card,
        .strategy-section,
        .compact-arrival-chart,
        .report-memo-card,
        .history-purpose-card {
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        .page-header,
        .section-header,
        .metric-card-compact,
        .kpi-card,
        .scenario-card,
        .report-card,
        .excel-card,
        .next-action-panel,
        .excel-readonly-panel,
        .report-memo-card,
        .history-purpose-card {
            overflow: hidden;
        }

        .text-truncate {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .line-clamp-2 {
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .pace-mode-card {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(260px, 0.86fr);
            align-items: center;
            gap: 5px 14px;
            margin: 6px 0 12px !important;
            padding: 12px 14px !important;
            border: 1px solid #bdd8d4;
            border-left: 4px solid var(--teal);
            border-radius: 8px;
            background: var(--surface);
            box-shadow: 0 1px 2px rgba(28, 39, 49, 0.06);
        }

        .pace-mode-card.status-under-target {
            border-color: #e5c5bd;
            border-left-color: #b76351;
            background: #fff8f6;
        }

        .pace-mode-card.status-on-target {
            border-color: #e7d1a7;
            border-left-color: var(--amber);
            background: #fffaf0;
        }

        .pace-mode-card.status-over-target {
            border-color: #bfdcc9;
            border-left-color: #2d8b67;
            background: #f5fbf7;
        }

        .pace-mode-card__label {
            grid-column: 1;
            color: var(--text-muted);
            font-size: var(--font-overline) !important;
            font-weight: 700 !important;
            line-height: 1.2 !important;
        }

        .pace-mode-card__mode {
            grid-column: 1;
            margin-top: 1px;
            color: var(--text-main);
            font-size: 24px !important;
            font-weight: 800 !important;
            line-height: 1.15 !important;
            overflow-wrap: anywhere;
        }

        .pace-mode-card.status-under-target .pace-mode-card__mode {
            color: #854234;
        }

        .pace-mode-card.status-on-target .pace-mode-card__mode {
            color: #805113;
        }

        .pace-mode-card.status-over-target .pace-mode-card__mode {
            color: #1d6446;
        }

        .pace-mode-card__description {
            grid-column: 1;
            margin-top: 2px;
            color: var(--text-muted);
            font-size: var(--font-body) !important;
            line-height: 1.45 !important;
            overflow-wrap: anywhere;
        }

        .pace-mode-card__facts {
            grid-column: 2;
            grid-row: 1 / span 3;
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 0;
            min-width: 0;
        }

        .pace-mode-card__fact {
            min-width: 0;
            padding: 9px 10px;
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.72);
        }

        .pace-mode-card__fact small {
            display: block;
            color: var(--text-muted) !important;
            font-size: var(--font-overline) !important;
            font-weight: 500 !important;
            line-height: 1.25 !important;
        }

        .pace-mode-card__fact strong {
            display: block;
            margin-top: 4px;
            color: var(--text-main);
            font-size: var(--font-metric-value) !important;
            font-weight: 700 !important;
            line-height: 1.22 !important;
            overflow-wrap: anywhere;
        }

        [data-testid="stMetric"] {
            height: 100px !important;
            min-height: 100px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            border-radius: 8px !important;
            background: var(--surface) !important;
        }

        [data-testid="stMetric"] > div {
            min-height: 0 !important;
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] p {
            font-size: var(--font-overline) !important;
            line-height: 1.3 !important;
        }

        [data-testid="stMetricValue"] {
            font-size: var(--font-metric-value) !important;
            font-weight: 700 !important;
            line-height: 1.25 !important;
            margin-top: 8px !important;
            overflow-wrap: anywhere;
        }

        [data-testid="stMetricDelta"] {
            font-size: var(--font-overline) !important;
            line-height: 1.25 !important;
            margin-top: 6px !important;
        }

        .kpi-grid {
            grid-template-columns: repeat(7, minmax(0, 1fr)) !important;
            gap: 8px !important;
        }

        .kpi-card {
            min-height: 0 !important;
            padding: 10px 11px !important;
            border-radius: 8px !important;
            line-height: 1.5 !important;
        }

        .kpi-card__label {
            font-size: 12px !important;
            font-weight: 700 !important;
            line-height: 1.3 !important;
        }

        .kpi-card__value {
            font-size: 17px !important;
            font-weight: 700 !important;
            line-height: 1.25 !important;
            margin-top: 9px !important;
            overflow-wrap: anywhere;
        }

        .kpi-card__sub {
            font-size: 12px !important;
            font-weight: 400 !important;
            line-height: 1.38 !important;
            margin-top: 8px !important;
            overflow-wrap: anywhere;
        }

        .metric-card-compact {
            min-height: 0;
            height: auto;
            padding: 9px 10px;
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            background: var(--surface);
        }

        .metric-card-compact span {
            color: var(--text-muted);
            font-size: var(--font-overline);
            font-weight: 700;
            line-height: 1.32;
        }

        .metric-card-compact strong {
            font-size: var(--font-metric-value);
            font-weight: 700;
            line-height: 1.3;
            overflow-wrap: anywhere;
        }

        .report-card__rail {
            margin-bottom: 16px !important;
        }

        .report-card__body {
            display: grid;
            gap: 0;
            margin: 0;
            color: var(--text-main);
            font-family: var(--font-sans) !important;
            white-space: normal;
        }

        .report-card__section {
            padding: 0 0 15px;
            margin: 0 0 15px;
            border-bottom: 1px solid var(--line-soft);
        }

        .report-card__section:last-child {
            padding-bottom: 0;
            margin-bottom: 0;
            border-bottom: 0;
        }

        .report-card__section-title {
            margin: 0 0 9px !important;
            color: var(--text-main);
            font-size: 13px !important;
            font-weight: 800 !important;
            line-height: 1.35 !important;
            letter-spacing: 0 !important;
        }

        .report-card__list {
            display: grid;
            gap: 8px;
            margin: 0;
            padding-left: 18px;
        }

        .report-card__list li,
        .report-card__paragraph {
            color: var(--text-main);
            font-size: 13px !important;
            line-height: 1.72 !important;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        .report-card__paragraph {
            margin: 0;
        }

        .report-card__placeholder {
            color: var(--text-muted);
        }

        .chart-first-grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(300px, 340px);
            gap: 14px;
            align-items: stretch;
        }

        div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head) {
            display: grid !important;
            grid-template-columns: minmax(0, 1fr) minmax(300px, 340px) !important;
            gap: 16px !important;
            align-items: stretch !important;
            margin-top: 14px !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head) > div {
            display: flex !important;
            width: 100% !important;
            min-width: 0 !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head) > div > div,
        div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head) div[data-testid="stVerticalBlock"],
        div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head) div[data-testid="stMarkdownContainer"]:has(.decision-panel) {
            width: 100% !important;
            height: 100% !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) {
            display: flex !important;
            flex-direction: column !important;
            height: 100% !important;
            border: 1px solid var(--line-soft) !important;
            border-radius: 8px !important;
            background: var(--chart-bg) !important;
            padding: 14px 16px 12px !important;
            box-shadow: 0 1px 2px rgba(28, 39, 49, 0.06) !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) .projection-chart-card {
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            border-radius: 0 !important;
            background: var(--chart-bg) !important;
            box-shadow: none !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) .projection-chart-card__head {
            background: var(--chart-bg) !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) details,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) [data-testid="stElementContainer"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) div[data-testid="stMarkdownContainer"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) div[data-testid="stVegaLiteChart"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) div[data-testid="stVegaLiteChart"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) canvas,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) svg {
            background: var(--chart-bg) !important;
        }

        .projection-chart-card,
        .decision-panel,
        .report-card,
        .excel-card,
        .empty-state,
        .strategy-section,
        .next-action-panel,
        .excel-readonly-panel,
        .compact-arrival-chart,
        .report-memo-card,
        .history-purpose-card {
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            background: var(--surface);
            box-shadow: 0 1px 2px rgba(28, 39, 49, 0.06);
        }

        .projection-chart-card {
            padding: 0;
            min-height: 0;
            border: 0;
            box-shadow: none;
        }

        .projection-chart-card__head {
            gap: 12px;
            margin-bottom: 6px;
        }

        .projection-chart-card__copy {
            max-width: 760px;
            margin-top: 3px;
            line-height: 1.55 !important;
        }

        .chart-legend-row {
            gap: 8px 14px;
            padding: 9px 0 0;
            margin-bottom: 10px;
            color: var(--text-muted);
            font-size: var(--font-chart-legend) !important;
            font-weight: 500;
            line-height: 1.42;
        }

        .chart-legend-row span {
            min-width: 0;
            white-space: normal;
        }

        .chart-legend-row i {
            width: 18px;
            border-top-width: 3px;
        }

        .chart-legend-row .legend-target {
            border-color: #8a94a1;
            border-top-style: dashed;
        }

        .chart-legend-row .legend-actual {
            border-color: var(--teal);
        }

        .chart-legend-row .legend-projection {
            border-color: var(--amber);
            border-top-style: dashed;
        }

        .chart-legend-row .legend-band {
            background: rgba(183, 121, 31, 0.16);
        }

        .chart-legend-row .legend-close {
            border-color: var(--slate);
            border-top-style: dashed;
        }

        .chart-legend-row .legend-current {
            background: var(--text-main);
        }

        .projection-chart-caption {
            clear: both;
            display: block;
            margin: 8px 0 0;
            padding-top: 8px;
            border-top: 1px solid var(--line-soft);
            color: var(--text-muted);
            font-size: var(--font-caption) !important;
            line-height: 1.6 !important;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        div[data-testid="stMarkdownContainer"]:has(.scenario-inline-chart-title) {
            display: block !important;
            margin: 10px 0 12px !important;
            position: relative;
            z-index: 1;
        }

        .scenario-inline-chart-title {
            display: grid !important;
            grid-template-columns: auto minmax(0, 1fr);
            align-items: end;
            gap: 4px 10px;
            width: 100%;
            min-height: 28px;
            margin: 0 !important;
            padding: 0 0 4px;
            color: var(--text-main);
            line-height: 1.35 !important;
            overflow: visible;
        }

        .scenario-inline-chart-title strong,
        .scenario-inline-chart-title span {
            display: block;
            min-width: 0;
            line-height: 1.35 !important;
            overflow-wrap: anywhere;
        }

        .scenario-inline-chart-title strong {
            font-size: var(--font-body) !important;
            font-weight: 800 !important;
        }

        .scenario-inline-chart-title span {
            color: var(--text-muted);
            font-size: var(--font-overline) !important;
            font-weight: 500 !important;
        }

        div[data-testid="stAlert"] {
            clear: both;
            position: relative;
            z-index: 0;
        }

        .decision-panel {
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            min-height: 100%;
            padding: 14px;
        }

        .decision-panel__row {
            grid-template-columns: 96px minmax(0, 1fr);
            align-items: center;
            gap: 12px;
            width: 100%;
            min-height: 34px;
            padding: 7px 0;
        }

        .decision-panel__row span {
            min-width: 0;
            font-size: var(--font-caption) !important;
            font-weight: 500 !important;
            line-height: 1.38 !important;
        }

        .decision-panel__row strong {
            font-size: var(--font-body) !important;
            font-weight: 600 !important;
            line-height: 1.38 !important;
            max-width: 100%;
            overflow-wrap: anywhere;
        }

        .decision-panel__row:last-child {
            align-items: start;
            padding-bottom: 0;
        }

        .workbench-fact-row {
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 10px;
        }

        .strategy-section .scenario-card__description {
            max-height: none;
        }

        .strategy-section {
            padding: 12px;
            margin: 10px 0 14px;
        }

        .strategy-section.is-active-management {
            border-top: 3px solid rgba(20, 117, 111, 0.55);
            background: #fbfefe;
        }

        .strategy-section__head {
            gap: 14px;
            margin-bottom: 10px;
        }

        .strategy-section__head p {
            line-height: 1.55 !important;
        }

        .strategy-section__head span {
            display: inline-flex;
            align-items: center;
            min-width: 0;
            border: 0;
            background: transparent;
            color: #0f665e;
            padding: 0;
            font-size: var(--font-overline) !important;
            font-weight: 700 !important;
            line-height: 1.3 !important;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        .strategy-card-shell__badge {
            display: inline-flex;
            align-items: center;
            min-width: 0;
            border: 1px solid var(--line-soft);
            border-radius: 999px;
            background: var(--surface-muted);
            color: var(--text-muted);
            padding: 3px 7px;
            font-size: var(--font-overline) !important;
            font-weight: 700 !important;
            line-height: 1.3 !important;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        .strategy-card-shell__head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 8px;
            min-width: 0;
            margin-bottom: 5px;
        }

        .strategy-card-shell__badge.is-reference {
            border-color: var(--line-soft);
            background: var(--surface-muted);
            color: var(--text-muted);
        }

        .strategy-card-shell__badge.is-recommended-badge {
            border-color: #bdd8d4;
            background: #e9f5f2;
            color: #0f665e;
        }

        .strategy-card-active {
            border-left: 0;
            border-radius: 0;
            padding-left: 0;
        }

        .strategy-card-active .scenario-card {
            border-color: var(--line-soft) !important;
            box-shadow: none !important;
        }

        .strategy-card-active.is-recommended .scenario-card {
            border-left: 1px solid rgba(20, 117, 111, 0.2) !important;
            background: #f7fcfa;
            box-shadow: inset 0 0 0 1px rgba(20, 117, 111, 0.16) !important;
        }

        .strategy-card-shell__code {
            line-height: 1.35 !important;
            overflow-wrap: anywhere;
        }

        .strategy-section .scenario-card {
            min-height: 0;
        }

        .strategy-section .scenario-card.is-emphasis {
            box-shadow: none !important;
        }

        .strategy-card-active.is-recommended .scenario-card.is-emphasis {
            box-shadow: inset 0 0 0 1px rgba(20, 117, 111, 0.16) !important;
        }

        .strategy-section .status-badge {
            border-color: transparent;
            background: transparent;
            color: #0f665e;
            padding: 0;
            gap: 5px;
            font-size: 11px !important;
            box-shadow: none;
        }

        .strategy-section .status-badge::before {
            width: 6px;
            height: 6px;
            opacity: 0.72;
        }

        .strategy-section .scenario-card__name {
            font-size: 14px !important;
            line-height: 1.35 !important;
        }

        .strategy-section .scenario-card__description {
            font-size: 12px !important;
            line-height: 1.5 !important;
        }

        .strategy-section .scenario-card__metric-label {
            font-size: 11px !important;
            line-height: 1.32 !important;
        }

        .strategy-section .scenario-card__metric-value {
            font-size: 12px !important;
            line-height: 1.35 !important;
        }

        .report-ia-note,
        .history-purpose-card {
            margin: 8px 0 12px;
            padding: 12px 14px;
            color: var(--text-main);
            font-size: var(--font-body) !important;
            line-height: var(--line-card) !important;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        .report-meta-row,
        .history-question-grid,
        .history-next-actions {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: 8px 0 12px;
        }

        .report-meta-row span,
        .history-question-grid span,
        .history-next-actions span {
            display: block;
            min-width: 0;
            padding: 9px 10px;
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            background: var(--surface-muted);
            color: var(--text-main);
            font-size: var(--font-caption) !important;
            line-height: 1.55 !important;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        .report-memo-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin: 8px 0 12px;
        }

        .report-memo-card {
            padding: 12px;
            min-height: 0;
        }

        .report-memo-card strong {
            display: block;
            margin-bottom: 5px;
            color: var(--text-main);
            font-size: var(--font-card-title);
            font-weight: 700;
            line-height: var(--line-tight);
        }

        .report-memo-card span {
            display: block;
            color: var(--text-muted);
            font-size: var(--font-body);
            line-height: var(--line-card);
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        textarea[aria-label="복사용 보고문"],
        textarea[aria-label="보고 메모"] {
            min-height: 320px;
            font-family: var(--font-sans) !important;
            font-size: var(--font-body-large) !important;
            line-height: 1.6 !important;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }

        .history-purpose-card h3 {
            margin: 0 0 6px !important;
            padding: 0 !important;
            border: 0 !important;
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
            min-width: 0;
            overflow: auto;
        }

        div[data-testid="stDataFrame"] *,
        div[data-testid="stTable"] *,
        [data-testid="stDataEditor"] * {
            font-family: var(--font-sans) !important;
            font-size: var(--font-caption) !important;
            line-height: 1.5 !important;
        }

        @media (max-width: 1180px) {
            .chart-first-grid,
            div[data-testid="stHorizontalBlock"]:has(.projection-chart-card__head) {
                grid-template-columns: 1fr !important;
            }

            .decision-panel {
                width: 100%;
            }

            .workbench-fact-row,
            .report-meta-row,
            .history-question-grid,
            .history-next-actions {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 900px) {
            section[data-testid="stSidebar"] {
                width: 100% !important;
            }

            .block-container {
                padding-top: 2rem !important;
            }

            .same-window-top-status {
                grid-template-columns: 1fr;
                align-items: start;
                margin-top: 18px;
            }

            .same-window-top-status__meta {
                justify-content: flex-start;
            }
        }

        @media (max-width: 760px) {
            .pace-mode-card {
                grid-template-columns: 1fr;
                padding: 12px 14px !important;
            }

            .pace-mode-card__mode {
                font-size: 22px !important;
            }

            .pace-mode-card__facts {
                grid-column: 1;
                grid-row: auto;
                grid-template-columns: 1fr;
                margin-top: 6px;
            }

            .workbench-fact-row,
            .report-meta-row,
            .report-memo-grid,
            .history-question-grid,
            .history-next-actions {
                grid-template-columns: 1fr;
            }

            .scenario-inline-chart-title {
                grid-template-columns: 1fr;
                align-items: start;
            }

            .pace-pill {
                max-width: 100%;
            }
        }
        </style>
        """


def get_app_styles_css() -> str:
    """Return the app-owned CSS layers in injection order."""
    return "\n".join((get_app_base_styles_css(), get_app_layout_styles_css()))


def inject_app_styles(st_module: Any | None = None, pace_css: str | None = None) -> None:
    """Inject app shell styles into Streamlit, preserving the original layer order."""
    if st_module is None:
        import streamlit as st_module

    st_module.markdown(get_app_base_styles_css(), unsafe_allow_html=True)
    if pace_css:
        st_module.markdown(pace_css, unsafe_allow_html=True)
    st_module.markdown(get_app_layout_styles_css(), unsafe_allow_html=True)
    st_module.markdown(get_global_styles(), unsafe_allow_html=True)
