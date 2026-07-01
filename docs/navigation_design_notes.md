# U02 Navigation Design Notes

## Information Architecture

U02 changes the app from a long single Streamlit page into an internal router
that keeps one calculation context and renders business pages by route key.

Required pages:

- `home`: front page summary for 마감 페이스 체크.
- `input`: upload, sample loading, input table, is_close_day status, validation.
- `forecast`: KPI, F1/F2/F3 forecast result, target status, next close requirement.
- `scenarios`: P1/P2/P3, O1/O2/O3, Neutral/Maintain, full ScenarioGrid.
- `report`: report_builder.py memo and copy area.
- `history`: ForecastHistory, FinalActuals, Backtest, ModelWeights, ConfidenceBand, Insights.
- `excel`: latest Excel download and ScenarioGrid column check.
- `audit`: pytest, Gate Runner, forbidden pattern, security and operation notes.

## Router

The app uses an app.py internal router instead of a Streamlit `pages/` folder.
This keeps uploaded input, direct edits, selected metric, selected as-of date,
scenario choice, and latest calculation context in the same session.

The current page is resolved from:

- URL query param `page`.
- `st.session_state` fallback.
- Safe fallback to `home` for unknown keys.

## Navigation Policy

U02 implements:

- Sticky topbar on every page.
- Left navigation rail in the Streamlit sidebar.
- Session-state collapsed/expanded rail.
- Active page styling through `nav-item active`.
- Top mini navigation links for cross-page movement.

The topbar displays:

- App name: 마감 페이스 체크 / Month-End Pace Check.
- Current page title.
- 기준월.
- 영업일 n / total.
- 마감일 여부.
- 운영모드.

## Password Gate

U02 temporarily disables the runtime Auth Gate for local audit and screenshot
convenience. The helper remains in app.py for a later R01 restoration path, but
main() does not call it and therefore does not read Streamlit secrets during
normal U02 app entry.

Before any external or shared operation, R01 must restore an Auth Gate and
confirm access-control behavior.

## Guardrails

- Calculation modules were not changed for navigation.
- is_close_day remains the only close-day decision source.
- day_name remains display-only.
- No external CDN, font, image, or remote CSS dependency is used.
- archive_invalid and archive_old_format remain outside the default sharing path.
