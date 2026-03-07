# Tooling Guide — unified-ui SDK

This document describes the development tooling, workflows, and quality gates for the unified-ui SDK.

## Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Python | 3.13+ | [python.org](https://www.python.org/downloads/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| pre-commit | latest | `pip install pre-commit` |
| commitlint | latest | `npm install -g @commitlint/cli @commitlint/config-conventional` |

## Quick Commands

```bash
# Development
uv sync                                       # Install/update dependencies
uv sync --frozen                              # Install from lockfile (CI)

# Testing
pytest tests/ -n auto --no-header -q                              # Run all tests (parallel)
pytest tests/ -n auto --cov=unifiedui_sdk --cov-report=html       # With coverage
pytest tests/ -n auto --cov=unifiedui_sdk --cov-fail-under=80     # CI coverage gate

# Code Quality
ruff check .                                  # Lint
ruff format .                                 # Format
ruff check . && ruff format --check .         # CI check (lint + format verify)
mypy src/unifiedui_sdk/                       # Type check

# Build & Publish
uv build                                      # Build sdist + wheel
uv publish                                    # Publish to PyPI
```

## Pre-commit Hooks

Install hooks once per clone:

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

Hooks run automatically on `git commit`. Manual run:

```bash
pre-commit run --all-files
```

### Configured Hooks

| Hook | Source | Purpose |
|------|--------|---------|
| trailing-whitespace | pre-commit-hooks | Remove trailing whitespace |
| end-of-file-fixer | pre-commit-hooks | Ensure files end with newline |
| check-yaml | pre-commit-hooks | Validate YAML syntax |
| check-toml | pre-commit-hooks | Validate TOML syntax |
| check-added-large-files | pre-commit-hooks | Prevent large files (>500KB) |
| check-merge-conflict | pre-commit-hooks | Detect merge conflict markers |
| debug-statements | pre-commit-hooks | Detect leftover debug statements |
| ruff (lint) | ruff-pre-commit | Lint with auto-fix |
| ruff-format | ruff-pre-commit | Code formatting |
| commitlint | commitlint-pre-commit | Enforce Conventional Commits |

## Commit Convention

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

**Examples**:
```
feat(tracing): add LangChain callback handler
fix(streaming): handle empty response chunks
docs(readme): update installation instructions
chore(deps): update ruff to 0.11.8
```

## Code Quality Gates

### Linting & Formatting (Ruff)

Configuration: `pyproject.toml` → `[tool.ruff]`

Enabled rules:
- `E` / `W` — pycodestyle (errors/warnings)
- `F` — pyflakes
- `I` — isort (import sorting)
- `N` — pep8-naming
- `UP` — pyupgrade
- `B` — flake8-bugbear
- `SIM` — flake8-simplify
- `TC` — flake8-type-checking
- `RUF` — ruff-specific rules
- `D` — pydocstyle (Google convention)

### Type Checking (mypy)

Configured in `pyproject.toml`:

```ini
strict = true
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
```

### Testing

- Minimum coverage: **80%**
- Test location: `tests/` directory
- Naming: `test_<module>.py`
- Parallelisation: `-n auto` (pytest-xdist)
- Markers: `unit`, `integration`, `slow`

## CI/CD Workflows

| Workflow | Trigger | Job |
|----------|---------|-----|
| `ci-tests-and-lint.yml` | push/PR to `main` | Tests, ruff lint, ruff format, mypy, coverage |
| `ci-pr-branch-check.yml` | PR open/sync | Branch naming convention check |
| `codeql.yml` | push/PR/weekly | Security scanning (CodeQL) |

## Security

- **CodeQL** scans for vulnerabilities on every push and weekly
- **Ruff** includes security rules via flake8-bugbear
- **pre-commit** hooks prevent accidental debug statements and large files

## IDE Configuration

### VS Code

Recommended extensions:
- `ms-python.python`
- `charliermarsh.ruff`
- `EditorConfig.EditorConfig`

Settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "ruff.lint.args": ["--config=pyproject.toml"]
}
```
