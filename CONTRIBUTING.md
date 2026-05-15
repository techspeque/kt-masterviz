# Contributing to kt-masterviz

Thanks for your interest. This document is the index — most of the actual
machinery lives in `scripts/`, and this file just tells you which script to run
when.

## Quick start

```bash
git clone https://github.com/techspeque/kt-masterviz.git
cd kt-masterviz
bash scripts/prereqs.sh
```

`prereqs.sh` installs `uv` (if missing), provisions Python 3.12, and syncs the
dev dependency group into `.venv/`. It's idempotent — safe to re-run any time.

## Development loop

```bash
# edit code
bash scripts/test.sh                  # full suite + coverage
bash scripts/test.sh -k loader        # subset; args pass through to pytest
bash scripts/test.sh -x --pdb         # stop on first failure, drop into pdb
```

To run exactly what CI runs (prereqs + tests) before pushing:

```bash
bash scripts/ci.sh
```

The GitHub workflow invokes the same script, so "passes locally" implies
"passes in CI" by construction.

### Running the dashboard locally

To poke at the UI while developing, you need a CSV to point at. The easiest
way to get one is to run kt-masterlog's test suite — it produces real master
CSVs in `tmp_path`. Or write a small one by hand:

```bash
cat > /tmp/sample.csv <<EOF
trial_id,epoch,lr,units,loss,val_loss
0001,1,0.001,64,0.82,0.91
0001,2,0.001,64,0.65,0.74
0002,1,0.0003,128,0.79,0.85
EOF

uv run kt-masterviz /tmp/sample.csv
```

Streamlit hot-reloads on file changes in `src/kt_masterviz/dashboard.py`, so
the dev loop is: edit → save → browser refreshes.

## Submitting changes

1. Fork the repo and create a topic branch from `main`.
2. Make your change with tests.
3. Push the branch and open a PR against `main`.
4. CI must be green before merge.

### Commit message format

Commits use the [Conventional Commits](https://www.conventionalcommits.org/)
prefix. The `CHANGELOG.md` is generated from these by `git-cliff` during
releases, so good prefixes mean good release notes for free.

| Prefix | Goes under | Example |
|--------|-----------|---------|
| `feat:` | Added | `feat: add registry-based run picker` |
| `fix:` | Fixed | `fix: handle partial CSV lines without dropping data` |
| `perf:` | Performance | `perf: skip Streamlit file watcher` |
| `refactor:` | Changed | `refactor: split dashboard into picker + viewer` |
| `docs:` | Documentation | `docs: document the registry schema` |
| `test:` | Tests | `test: add Playwright smoke test` |
| `chore(deps):` | Dependencies | `chore(deps): bump streamlit to 1.45` |
| `ci:` | CI/CD | `ci: cache Playwright browsers between runs` |
| `build:` | Build | `build: switch to dynamic version via hatchling` |
| *(other)* | Miscellaneous | (drops into a catch-all bucket — try to use one above) |

Breaking changes: append `!` to the prefix (`feat!:`) or include a
`BREAKING CHANGE:` footer in the commit body. These render with a
**BREAKING** marker in the changelog.

Preview what the next release's notes will look like at any time:

```bash
bash scripts/changelog.sh                # the [Unreleased] section
bash scripts/changelog.sh --tag v0.2.0   # as if 0.2.0 were cut now
```

What CI checks:

- **`ci.yml`** — runs on every push and PR. Executes the full pytest suite
  with coverage on Python 3.12.
- **`build-check.yml`** — runs on PRs to `main`. Builds the wheel and sdist
  to catch packaging regressions.

## Coding expectations

- **Tests required.** New behavior needs a test; bug fixes need a regression
  test that fails without the fix.
- **Match the surrounding code.** No formal style guide; the codebase is small
  enough that imitation is the easiest path.
- **Be conservative about new dependencies.** Streamlit is already a heavy
  dep. New runtime deps need a clear justification; dev-only deps go in
  `[dependency-groups] dev` and `[project.optional-dependencies] dev` in
  `pyproject.toml`.
- **No dependency on kt-masterlog.** The two packages share a file format,
  not Python code. Keeping them decoupled is the whole point — don't reach
  for `from kt_masterlog import ...`.

## Reporting bugs

Open an issue at
[github.com/techspeque/kt-masterviz/issues](https://github.com/techspeque/kt-masterviz/issues).
Please include the CSV (or a minimal reproduction of one) and the kt-masterviz
version (`kt-masterviz --help` shows it, or `python -c "import kt_masterviz; print(kt_masterviz.__version__)"`).

## Release process (maintainers only)

Releases are driven by version tags. `release.sh` regenerates
`CHANGELOG.md` from conventional commits via `git-cliff` and rolls
the result into the release commit — you don't write the changelog
by hand. Just commit using the
[conventional prefixes](#commit-message-format) and run:

```bash
bash scripts/release.sh 0.2.0
```

This script is strict — it refuses to run with a dirty tree, off `main`, or
with a tag that already exists. It runs CI, bumps `__version__`, refreshes
`uv.lock`, commits, tags `v0.2.0`, and builds the wheel locally as a sanity
check. Nothing leaves your machine.

To publish, push the commit and tag:

```bash
git push origin main
git push origin v0.2.0
```

The tag push triggers `.github/workflows/release.yml`, which:

1. Verifies the tag matches `__version__` (a forgotten `version.sh` bump
   fails loudly instead of shipping a mismatched release).
2. Runs the full CI suite as a final gate.
3. Builds the wheel + sdist.
4. Publishes to PyPI via [trusted
   publishing](https://docs.pypi.org/trusted-publishers/) — no token
   secrets required.
5. Creates a GitHub Release with auto-generated notes and attaches the
   wheel + sdist as downloadable assets. Pre-release tags (`-rc1`, `-beta`,
   etc.) are auto-marked as GitHub pre-releases.

### One-time PyPI setup

Before the first release, configure a trusted publisher at
[pypi.org/manage/account/publishing](https://pypi.org/manage/account/publishing/):

- PyPI Project Name: `kt-masterviz`
- Owner: `techspeque`
- Repository: `kt-masterviz`
- Workflow name: `release.yml`
- Environment: *(leave blank)*

After the first successful publish, the publisher entry is locked in
permanently.
