"""Local CSS skin for the Streamlit pace-check interface."""

from __future__ import annotations


def get_pace_check_css() -> str:
    """Return local-only CSS for the Month-End Pace Check skin."""
    return """
    <style>
    :root {
        --bg: #f5f2ec;
        --surface: #fffdf8;
        --surface-2: #f9f6ef;
        --surface-3: #eee8dd;

        --ink: #20262d;
        --ink-2: #515b65;
        --muted: #858c94;

        --line: #ded6ca;
        --line-2: #cfc5b7;

        --teal: #16877d;
        --teal-soft: #e7f3ef;

        --amber: #be7a1b;
        --amber-soft: #fbefd8;

        --clay: #b76351;
        --clay-soft: #f6e7e2;

        --green: #2d8b67;
        --green-soft: #e6f2eb;

        --blue: #51758c;
        --blue-soft: #e8eff3;

        --radius-lg: 22px;
        --radius-md: 16px;

        --shadow-focus: 0 16px 42px rgba(38, 55, 48, .12), 0 2px 0 rgba(255,255,255,.95) inset;
        --shadow-soft: 0 8px 22px rgba(38, 55, 48, .07);
    }

    .stApp {
        background: var(--bg) !important;
        color: var(--ink) !important;
    }

    [data-testid="stHeader"] {
        background: var(--bg) !important;
        border-bottom: 1px solid var(--line) !important;
    }

    .block-container {
        max-width: 1480px;
        padding-top: 1rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3,
    p, li, label,
    div[data-testid="stMarkdownContainer"] {
        color: var(--ink) !important;
        letter-spacing: 0 !important;
    }

    h1,
    .pace-hero-title {
        font-family: "Noto Serif CJK KR", "Nanum Myeongjo", "AppleMyungjo", serif !important;
    }

    h2 {
        border-top: 1px solid var(--line) !important;
        color: var(--ink) !important;
    }

    h3 {
        color: var(--ink) !important;
    }

    div[data-testid="stCaptionContainer"],
    div[data-testid="stCaptionContainer"] p,
    small {
        color: var(--ink-2) !important;
    }

    .pace-check-shell {
        color: var(--ink);
        margin: 0 0 22px;
    }

    .pace-topbar {
        min-height: 56px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        padding: 10px 16px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: var(--surface);
    }

    .pace-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--ink-2);
        font-size: 13px;
        font-weight: 900;
        letter-spacing: 0;
    }

    .pace-brand small {
        display: block;
        margin-top: 2px;
        color: var(--muted) !important;
        font-size: 11px;
        font-weight: 760;
        letter-spacing: 0;
    }

    .pace-brand-mark {
        width: 28px;
        height: 28px;
        border: 2px solid var(--teal);
        border-radius: 8px;
        background: var(--teal-soft);
        position: relative;
        flex: 0 0 auto;
    }

    .pace-brand-mark::after {
        content: "";
        position: absolute;
        left: 7px;
        top: 7px;
        width: 10px;
        height: 10px;
        border-right: 2px solid var(--teal);
        border-bottom: 2px solid var(--teal);
    }

    .pace-topbar-meta {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 8px;
    }

    .pace-topbar.is-sticky {
        position: sticky;
        top: .35rem;
        z-index: 20;
        box-shadow: 0 6px 16px rgba(38, 55, 48, .06);
    }

    .pace-current-page {
        color: var(--ink);
        font-size: 15px;
        font-weight: 900;
        white-space: nowrap;
    }

    .pace-pill {
        min-height: 32px;
        display: inline-flex;
        align-items: center;
        padding: 6px 11px;
        border: 1px solid var(--line);
        border-radius: 999px;
        background: var(--surface-2);
        color: var(--ink-2);
        font-size: 12px;
        font-weight: 780;
        line-height: 1.2;
        white-space: nowrap;
    }

    .pace-pill.is-primary {
        background: var(--teal-soft);
        border-color: #beddd6;
        color: #0f665e;
    }

    .pace-hero {
        margin-top: 18px;
        display: grid;
        grid-template-columns: 1fr;
        gap: 18px;
    }

    .pace-hero-main {
        min-height: 214px;
        border: 1px solid var(--line);
        border-radius: 26px;
        background: var(--surface);
        padding: 32px 34px;
    }

    .pace-eyebrow {
        display: inline-flex;
        align-items: center;
        min-height: 28px;
        padding: 6px 10px;
        border-radius: 999px;
        border: 1px solid #beddd6;
        background: var(--teal-soft);
        color: #0f665e;
        font-size: 12px;
        font-weight: 900;
        letter-spacing: 0;
        line-height: 1.2;
    }

    .pace-hero-title {
        margin: 16px 0 10px;
        color: var(--ink);
        font-size: 52px;
        line-height: 1.05;
        font-weight: 800;
    }

    .pace-hero-copy {
        margin: 0;
        max-width: 820px;
        color: var(--ink-2);
        font-size: 16px;
        line-height: 1.7;
    }

    .pace-chip-row {
        margin-top: 20px;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }

    .pace-chip {
        display: inline-flex;
        align-items: center;
        min-height: 36px;
        padding: 7px 12px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--surface-2);
        color: #4d5760;
        font-size: 13px;
        font-weight: 800;
        line-height: 1.2;
    }

    .download-card {
        box-shadow: var(--shadow-focus);
    }

    .pace-mode-card {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(260px, .86fr);
        align-items: center;
        gap: 5px 14px;
        border: 1px solid #b8d7d1;
        border-left: 4px solid var(--teal);
        border-radius: 8px;
        background: var(--surface);
        padding: 12px 14px;
        margin: 6px 0 12px;
        box-shadow: 0 1px 2px rgba(38, 55, 48, .06);
    }

    .pace-mode-card.status-under-target {
        border-color: #e5c5bd;
        border-left-color: var(--clay);
        background: #fff8f6;
    }

    .pace-mode-card.status-on-target {
        border-color: #e7d1a7;
        border-left-color: var(--amber);
        background: #fffaf0;
    }

    .pace-mode-card.status-over-target {
        border-color: #bfdcc9;
        border-left-color: var(--green);
        background: #f5fbf7;
    }

    .pace-mode-card__label {
        color: var(--muted);
        grid-column: 1;
        font-size: 11px;
        font-weight: 820;
        line-height: 1.2;
    }

    .pace-mode-card__mode {
        grid-column: 1;
        margin-top: 1px;
        color: var(--ink);
        font-size: 24px;
        line-height: 1.15;
        font-weight: 950;
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
        color: var(--ink-2);
        font-size: 13px;
        line-height: 1.45;
    }

    .pace-mode-card__facts {
        grid-column: 2;
        grid-row: 1 / span 3;
        margin-top: 0;
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
    }

    .pace-mode-card__fact {
        border: 1px solid var(--line);
        border-radius: 8px;
        background: rgba(255, 255, 255, .72);
        padding: 9px 10px;
    }

    .pace-mode-card__fact small {
        display: block;
        color: var(--muted) !important;
        font-size: 11px;
        font-weight: 820;
        line-height: 1.2;
    }

    .pace-mode-card__fact strong {
        display: block;
        margin-top: 4px;
        color: var(--ink);
        font-size: 16px;
        line-height: 1.22;
    }

    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(7, minmax(0, 1fr));
        gap: 8px;
        margin: 8px 0 14px;
    }

    .kpi-card {
        min-height: 0;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        padding: 10px 11px;
    }

    .kpi-card.is-focus {
        border-color: #b8d7d1;
        box-shadow: var(--shadow-soft);
    }

    .kpi-card.status-under-target {
        border-left: 4px solid var(--clay);
    }

    .kpi-card.status-on-target {
        border-left: 4px solid var(--amber);
    }

    .kpi-card.status-over-target {
        border-left: 4px solid var(--green);
    }

    .kpi-card__label {
        color: var(--muted);
        font-size: 12px;
        font-weight: 820;
        line-height: 1.3;
    }

    .kpi-card__value {
        margin-top: 9px;
        color: var(--ink);
        font-size: 17px;
        line-height: 1.25;
        font-weight: 950;
        overflow-wrap: anywhere;
    }

    .kpi-card__sub {
        margin-top: 8px;
        color: var(--muted);
        font-size: 12px;
        line-height: 1.38;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        min-height: 30px;
        border-radius: 999px;
        padding: 6px 10px;
        border: 1px solid #b8d7d1;
        background: var(--teal-soft);
        color: #0f665e;
        font-size: 12px;
        font-weight: 950;
        line-height: 1.2;
        white-space: nowrap;
    }

    .status-badge::before {
        content: "";
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--teal);
    }

    .status-badge.status-under-target {
        border-color: #e5c5bd;
        background: var(--clay-soft);
        color: #854234;
    }

    .status-badge.status-under-target::before {
        background: var(--clay);
    }

    .status-badge.status-on-target {
        border-color: #e7d1a7;
        background: var(--amber-soft);
        color: #805113;
    }

    .status-badge.status-on-target::before {
        background: var(--amber);
    }

    .status-badge.status-over-target {
        border-color: #bfdcc9;
        background: var(--green-soft);
        color: #1d6446;
    }

    .status-badge.status-over-target::before {
        background: var(--green);
    }

    .section-header {
        border-left: 4px solid var(--teal);
        padding: 4px 0 5px 12px;
        margin: 18px 0 11px;
    }

    .section-header__title {
        color: var(--ink);
        font-size: 18px;
        font-weight: 840;
        line-height: 1.2;
        margin: 0;
    }

    .section-header__subtitle {
        color: var(--ink-2);
        font-size: 13px;
        line-height: 1.45;
        margin-top: 5px;
    }

    .scenario-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(220px, 1fr));
        gap: 12px;
        margin: 8px 0 18px;
    }

    .scenario-card {
        min-height: 178px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: var(--surface);
        padding: 15px;
    }

    .scenario-card.is-emphasis {
        border-color: #bfdcc9;
        box-shadow: var(--shadow-soft);
    }

    .scenario-card--p {
        border-top: 3px solid var(--amber);
    }

    .scenario-card--o1,
    .scenario-card--o2,
    .scenario-card--o3 {
        border-top: 3px solid var(--green);
    }

    .scenario-card--neutral {
        border-top: 3px solid var(--blue);
    }

    .scenario-card__topline {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        align-items: flex-start;
        margin-bottom: 10px;
    }

    .scenario-card__id {
        color: var(--muted);
        font-size: 12px;
        font-weight: 780;
        overflow-wrap: anywhere;
    }

    .scenario-card__group {
        color: var(--ink-2);
        font-size: 11px;
        font-weight: 820;
        text-transform: uppercase;
    }

    .scenario-card__name {
        color: var(--ink);
        font-size: 18px;
        font-weight: 850;
        line-height: 1.2;
        margin-bottom: 8px;
    }

    .scenario-card__description {
        color: var(--ink-2);
        font-size: 12px;
        line-height: 1.5;
        min-height: 50px;
    }

    .scenario-card__metrics {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 12px;
    }

    .scenario-card__metric {
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 8px;
        background: var(--surface-2);
    }

    .scenario-card__metric-label {
        color: var(--muted);
        font-size: 11px;
        line-height: 1.2;
        margin-bottom: 4px;
    }

    .scenario-card__metric-value {
        color: var(--ink);
        font-size: 13px;
        font-weight: 820;
        line-height: 1.25;
        overflow-wrap: anywhere;
    }

    .report-card {
        border: 1px solid var(--line);
        border-radius: 20px;
        background: var(--surface);
        padding: 18px 20px 20px;
        margin: 8px 0 14px;
    }

    .report-card.is-focus {
        border-color: #b8d7d1;
        box-shadow: var(--shadow-soft);
    }

    .report-card__rail {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 14px;
    }

    .report-card__chip {
        border: 1px solid var(--line);
        border-radius: 999px;
        color: var(--ink-2);
        background: var(--surface-2);
        font-size: 11px;
        font-weight: 780;
        padding: 6px 9px;
    }

    .report-card__body {
        color: var(--ink);
        font-size: 14px;
        line-height: 1.65;
        margin: 0;
        font-family: inherit;
    }

    .report-card__section {
        padding: 0 0 16px;
        margin: 0 0 16px;
        border-bottom: 1px solid var(--line);
    }

    .report-card__section:last-child {
        padding-bottom: 0;
        margin-bottom: 0;
        border-bottom: 0;
    }

    .report-card__section-title {
        margin: 0 0 9px;
        color: var(--ink);
        font-size: 13px;
        font-weight: 850;
        line-height: 1.35;
    }

    .report-card__list {
        display: grid;
        gap: 8px;
        margin: 0;
        padding-left: 18px;
    }

    .report-card__list li,
    .report-card__paragraph {
        color: var(--ink);
        font-size: 13px;
        line-height: 1.72;
        overflow-wrap: anywhere;
        word-break: keep-all;
    }

    .report-card__paragraph {
        margin: 0;
    }

    .report-card__placeholder {
        color: var(--ink-2);
    }

    .history-card,
    .download-card {
        border: 1px solid var(--line);
        border-radius: 20px;
        background: var(--surface);
        padding: 16px;
        margin: 8px 0 14px;
    }

    .download-card {
        border-color: #b8d7d1;
    }

    .page-shell {
        margin-top: 14px;
    }

    .page-header {
        display: flow-root;
        min-width: 0;
        margin: 16px 0 14px;
        padding: 18px 20px;
        border: 1px solid var(--line);
        border-radius: 20px;
        background: var(--surface);
        overflow: hidden;
    }

    .page-header__eyebrow {
        color: var(--teal);
        font-size: 12px;
        font-weight: 900;
        letter-spacing: 0;
    }

    .page-header h1 {
        margin: 5px 0 0;
        color: var(--ink);
        font-size: 28px;
        line-height: 1.2;
        font-weight: 920;
        letter-spacing: 0;
    }

    .page-header__subtitle {
        margin-top: 8px;
        color: var(--ink-2);
        font-size: 14px;
        line-height: 1.55;
        overflow-wrap: anywhere;
    }

    .page-header > *:first-child,
    .section-header > *:first-child,
    .kpi-card > *:first-child,
    .scenario-card > *:first-child,
    .report-card > *:first-child,
    .download-card > *:first-child,
    .history-card > *:first-child,
    .detail-panel > *:first-child {
        margin-top: 0;
    }

    .page-header > *:last-child,
    .section-header > *:last-child,
    .kpi-card > *:last-child,
    .scenario-card > *:last-child,
    .report-card > *:last-child,
    .download-card > *:last-child,
    .history-card > *:last-child,
    .detail-panel > *:last-child {
        margin-bottom: 0;
    }

    .detail-panel {
        border: 1px solid var(--line);
        border-radius: 18px;
        background: var(--surface);
        padding: 16px;
        margin: 12px 0 16px;
    }

    .nav-rail {
        border: 1px solid var(--line);
        border-radius: 18px;
        background: var(--surface);
        padding: 12px;
        box-shadow: var(--shadow-soft);
    }

    .nav-rail.is-collapsed {
        padding: 10px;
    }

    .nav-rail__title {
        color: var(--muted);
        font-size: 12px;
        font-weight: 900;
        margin: 2px 2px 10px;
    }

    .nav-rail__items {
        display: grid;
        gap: 7px;
    }

    .nav-item {
        min-height: 38px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--surface-2);
        color: var(--ink-2) !important;
        padding: 8px 10px;
        font-size: 13px;
        font-weight: 820;
        text-decoration: none !important;
        line-height: 1.25;
    }

    .nav-item.active {
        border-color: #b8d7d1;
        background: var(--teal-soft);
        color: #0f665e !important;
    }

    .nav-item__marker {
        border: 1px solid #b8d7d1;
        border-radius: 999px;
        padding: 3px 6px;
        color: #0f665e;
        background: var(--surface);
        font-size: 10px;
        font-weight: 900;
        line-height: 1.1;
        white-space: nowrap;
    }

    .mini-nav,
    .pace-cta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 10px 0 14px;
    }

    .mini-nav .nav-item {
        min-height: 34px;
        flex: 0 1 auto;
    }

    .pace-cta {
        display: inline-flex;
        align-items: center;
        min-height: 40px;
        border: 1px solid #b8d7d1;
        border-radius: 12px;
        background: var(--teal-soft);
        color: #0f665e !important;
        padding: 9px 12px;
        font-size: 13px;
        font-weight: 900;
        text-decoration: none !important;
    }

    div[data-testid="stMetric"] {
        background: var(--surface) !important;
        border-color: var(--line) !important;
        border-left-color: var(--teal) !important;
        height: 100px !important;
        min-height: 100px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
    }

    div[data-testid="stMetric"] > div {
        min-height: 0 !important;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] p {
        color: var(--ink-2) !important;
    }

    [data-testid="stMetricValue"] {
        color: var(--ink) !important;
        margin-top: 8px !important;
    }

    [data-testid="stMetricDelta"] {
        margin-top: 6px !important;
    }

    div[data-testid="stAlert"],
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"],
    div[data-testid="stExpander"] details,
    div[data-testid="stFileUploader"] section {
        background: var(--surface) !important;
        border-color: var(--line) !important;
        color: var(--ink) !important;
    }

    div[data-testid="stDataFrame"] *,
    div[data-testid="stTable"] *,
    [data-testid="stDataEditor"] * {
        color: inherit;
    }

    div[data-testid="stTabs"] [role="tablist"] {
        border-bottom-color: var(--line) !important;
        gap: 4px;
    }

    button[data-baseweb="tab"] {
        border: 1px solid var(--line) !important;
        border-bottom: 0 !important;
        background: var(--surface-2) !important;
        color: var(--ink-2) !important;
        border-radius: 8px 8px 0 0 !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: var(--surface) !important;
        color: var(--teal) !important;
    }

    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button {
        background: var(--surface) !important;
        color: var(--ink) !important;
        border-color: var(--line-2) !important;
    }

    div[data-testid="stDownloadButton"] button {
        border-left: 4px solid var(--teal) !important;
    }

    textarea,
    input,
    div[data-baseweb="select"] > div {
        background: var(--surface) !important;
        color: var(--ink) !important;
        border-color: var(--line) !important;
    }

    @media (max-width: 1180px) {
        .scenario-grid {
            grid-template-columns: repeat(2, minmax(220px, 1fr));
        }
    }

    @media (max-width: 760px) {
        .pace-topbar,
        .pace-topbar-meta {
            align-items: flex-start;
            justify-content: flex-start;
        }

        .pace-topbar {
            flex-direction: column;
        }

        .pace-hero-main {
            padding: 22px 18px;
        }

        .pace-mode-card {
            grid-template-columns: 1fr;
            padding: 12px 14px;
        }

        .pace-hero-title {
            font-size: 36px;
        }

        .pace-mode-card__mode {
            font-size: 22px;
        }

        .kpi-card__value {
            font-size: 22px;
        }

        .pace-current-page {
            white-space: normal;
        }

        .pace-mode-card__facts,
        .kpi-grid,
        .scenario-grid,
        .scenario-card__metrics {
            grid-template-columns: 1fr;
        }

        .pace-mode-card__facts {
            grid-column: 1;
            grid-row: auto;
            margin-top: 6px;
        }

        .kpi-card,
        .scenario-card {
            min-height: auto;
        }
    }
    </style>
    """


def get_control_room_css() -> str:
    """Compatibility wrapper for legacy imports."""
    return get_pace_check_css()
