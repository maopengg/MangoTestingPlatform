# Mango Console Theme Guide

This project uses theme presets instead of one-off primary colors. Pages and components should read CSS variables written by `applyThemePreset`.

## Token Usage

- Page background: `--m-bg`
- Panel or card surface: `--m-surface`
- Soft panel background: `--m-surface-soft`
- Borders: `--m-border`, `--m-border-strong`
- Text: `--m-text`, `--m-text-2`, `--m-muted`
- Brand actions: `--m-primary`, `--m-primary-hover`, `--m-primary-soft`, `--m-primary-border`
- Semantic states: `--m-success`, `--m-danger`, `--m-warning`
- Tables: `--m-table-header-bg`, `--m-table-row-bg`, `--m-table-row-hover-bg`, `--m-table-border`, `--m-table-text`
- Forms: `--m-form-bg`, `--m-form-border`, `--m-form-hover-border`, `--m-form-focus-shadow`
- Overlays: `--m-overlay-bg`, `--m-overlay-border`, `--m-overlay-mask`
- Code and JSON: `--m-code-*`，固定为 PyCharm Darcula 风格，不随主题大幅变色
- Charts: `--m-chart-1` to `--m-chart-5`

## Rules

- New custom styles should prefer `--m-*` variables.
- Use semantic tokens for feedback. Do not use large high-saturation danger or warning backgrounds.
- Use chart tokens for dashboards and reports.
- Avoid hard-coded colors in `src/views`, `src/components`, and `src/layouts`.
- Keep `applyThemePreset(presetId)` as the only theme application entry.

## Allowed Exceptions

- Business enum colors from backend dictionaries.
- Image assets and screenshots.
- Chart fallback values used only when CSS variables are unavailable.
- Third-party component internals that cannot be themed through CSS variables.

## Audit

Run:

```bash
npm run theme:audit
```

The audit groups hard-coded colors into items that need review and allowed exceptions. The script is a development guardrail and is not currently wired into CI.
