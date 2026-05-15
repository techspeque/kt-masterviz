# Security Policy

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report them privately via [GitHub Security
Advisories](https://github.com/techspeque/kt-masterviz/security/advisories/new).
That channel is structured, traceable, and lets us coordinate a fix and
disclosure with you before the issue becomes public.

Please include:

- A description of the issue
- Steps to reproduce or a minimal proof-of-concept
- Affected version(s)

## Supported versions

This project is pre-1.0; only the latest released version on PyPI receives
security fixes.

## Scope

kt-masterviz is a thin dashboard layer over master CSVs produced by
kt-masterlog (or any CSV following the same schema). Vulnerabilities in
Streamlit, pandas, or other transitive dependencies should be reported
upstream to those projects.

Issues in our own code are in scope — examples:

- CSV parsing in `loader.py` (path-traversal, malformed-file handling)
- Streamlit app code in `dashboard.py`
- The CLI entry point in `cli.py`
- Anything in `scripts/` or `.github/workflows/` that could affect
  release integrity
