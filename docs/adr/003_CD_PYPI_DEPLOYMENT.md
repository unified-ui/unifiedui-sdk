# ADR-003: CD — Automatisches PyPI Deployment

**Status:** Proposed  
**Datum:** 2026-03-08  
**Autor:** Enrico Goerlitz

---

## 1. Kontext

Das `unifiedui-sdk` benötigt ein automatisiertes Deployment-Konzept für PyPI. Ziel ist es, nach einem Merge auf `main` automatisch eine neue Version zu veröffentlichen, ohne manuelle Eingriffe in die `pyproject.toml`.

### Anforderungen

- Automatisches Deployment nach PR-Merge auf `main`
- Versionierung basierend auf `pyproject.toml` als "Floor" (Major.Minor)
- Automatisches Inkrementieren der Patch-Version
- Git-Tag-Erstellung für jede Release-Version
- PyPI-Deployment via GitHub Actions

---

## 2. Entscheidung

### Option A: Floor-Based Auto-Versioning (Empfohlen)

Die Version in `pyproject.toml` definiert den **Mindest-Floor** für Major.Minor. Die Patch-Version wird automatisch basierend auf der aktuellen PyPI-Version inkrementiert.

#### Versionslogik

```
pyproject.toml    PyPI aktuell    Neue Version    Erklärung
─────────────────────────────────────────────────────────────────────
0.1.0             0.0.28          0.1.0           Major.Minor erhöht → Reset Patch
0.1.0             0.1.5           0.1.6           Gleicher Floor → Patch++
1.0.0             0.9.99          1.0.0           Major erhöht → Reset
1.20.0            1.19.28         1.20.0          Minor erhöht → Reset
2.0.0             1.99.99         2.0.0           Major erhöht → Reset
0.1.0             (nicht auf PyPI) 0.1.0          Erste Version
```

#### Algorithmus

```python
def calculate_next_version(floor_version: str, pypi_version: str | None) -> str:
    """
    Berechnet die nächste Version basierend auf Floor und PyPI.
    
    Args:
        floor_version: Version aus pyproject.toml (z.B. "0.1.0")
        pypi_version: Aktuelle Version auf PyPI oder None
    
    Returns:
        Nächste zu veröffentlichende Version
    """
    floor = parse_version(floor_version)  # (major, minor, patch)
    
    if pypi_version is None:
        return floor_version
    
    current = parse_version(pypi_version)
    
    # Floor ist höher als aktuell → verwende Floor
    if (floor.major, floor.minor) > (current.major, current.minor):
        return floor_version
    
    # Gleicher Major.Minor → inkrementiere Patch
    if (floor.major, floor.minor) == (current.major, current.minor):
        return f"{current.major}.{current.minor}.{current.patch + 1}"
    
    # Floor ist niedriger → inkrementiere PyPI-Version
    return f"{current.major}.{current.minor}.{current.patch + 1}"
```

#### Workflow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  PR auf main    │────▶│  CI Tests pass   │────▶│  Merge auf main │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌────────────────────┐
                                                 │  CD Workflow       │
                                                 │  (on: push main)   │
                                                 └────────┬───────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────────────────────────────┐
                        │                                 │                                 │
                        ▼                                 ▼                                 ▼
               ┌────────────────┐              ┌─────────────────┐              ┌───────────────────┐
               │ Read floor     │              │ Query PyPI      │              │ Calculate next    │
               │ from pyproject │              │ current version │              │ version           │
               └────────────────┘              └─────────────────┘              └─────────┬─────────┘
                                                                                          │
                                                                                          ▼
                                                                               ┌─────────────────────┐
                                                                               │ Create Git Tag      │
                                                                               │ (v{version})        │
                                                                               └─────────┬───────────┘
                                                                                         │
                                                                                         ▼
                                                                               ┌─────────────────────┐
                                                                               │ Build & Publish     │
                                                                               │ to PyPI             │
                                                                               └─────────────────────┘
```

#### Vorteile

- **Einfache Major/Minor-Releases**: Nur `pyproject.toml` ändern
- **Automatische Patch-Releases**: Jeder Merge → neue Patch-Version
- **Keine manuelle Versionspflege**: `pyproject.toml` bleibt stabil
- **Klare Semantik**: Floor definiert Mindest-Version

#### Nachteile

- **Komplexere Versionslogik**: Script zur Berechnung nötig
- **PyPI-Abhängigkeit**: Muss PyPI abfragen (kann fehlschlagen)
- **Verwirrung möglich**: `pyproject.toml` zeigt nicht die echte Version

---

### Option B: Manuelles Tagging (Alternative)

Developer erstellen manuell Tags für Releases. Das CD-Workflow deployed nur bei Tag-Push.

#### Workflow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  PR auf main    │────▶│  CI Tests pass   │────▶│  Merge auf main │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                 (kein automatisches Release)
                                                          
                                                          
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  git tag v1.2.3 │────▶│  git push --tags │────▶│  CD Workflow    │
└─────────────────┘     └──────────────────┘     │  (on: push tag) │
                                                 └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────────┐
                                                 │ Build & Publish     │
                                                 │ to PyPI             │
                                                 └─────────────────────┘
```

#### Vorteile

- **Einfach**: Keine komplexe Versionslogik
- **Kontrolle**: Volle Kontrolle über Release-Zeitpunkt
- **Transparent**: Tag-Version = PyPI-Version = `pyproject.toml`

#### Nachteile

- **Manueller Schritt**: Vergessen möglich
- **Doppelte Pflege**: Tag UND `pyproject.toml` müssen übereinstimmen
- **Langsamer**: Zusätzlicher Schritt nach dem Merge

---

## 3. Empfehlung

**Option A (Floor-Based Auto-Versioning)** wird empfohlen für:
- Häufige Releases
- Teams mit mehreren Contributors
- Continuous Deployment Philosophie

**Option B (Manuelles Tagging)** wird empfohlen für:
- Seltene, geplante Releases
- Einzelne Maintainer
- Projekte mit Breaking Changes in jedem Release

Für `unifiedui-sdk` wird **Option A** empfohlen, da:
1. Das SDK aktiv entwickelt wird
2. Häufige Patch-Releases erwartet werden
3. Automatisierung die Entwicklerproduktivität erhöht

---

## 4. Implementierung

### 4.1 Versioning Script

Datei: `scripts/calculate_version.py`

```python
#!/usr/bin/env python3
"""Calculate next version based on pyproject.toml floor and PyPI current version."""

import re
import subprocess
import sys
import tomllib
from pathlib import Path


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse semantic version string to tuple."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def get_floor_version() -> str:
    """Read version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def get_pypi_version(package_name: str) -> str | None:
    """Query current version from PyPI."""
    try:
        result = subprocess.run(
            ["pip", "index", "versions", package_name],
            capture_output=True,
            text=True,
            check=False,
        )
        # Parse output: "unifiedui-sdk (0.1.5)"
        match = re.search(rf"{package_name} \(([^)]+)\)", result.stdout)
        if match:
            return match.group(1)
    except Exception:
        pass
    
    # Fallback: Query PyPI API
    import urllib.request
    import json
    
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
            return data["info"]["version"]
    except Exception:
        return None


def calculate_next_version(floor: str, current: str | None) -> str:
    """Calculate next version based on floor and current PyPI version."""
    if current is None:
        return floor
    
    floor_parts = parse_version(floor)
    current_parts = parse_version(current)
    
    # Floor Major.Minor is higher → use floor
    if (floor_parts[0], floor_parts[1]) > (current_parts[0], current_parts[1]):
        return floor
    
    # Same Major.Minor → increment patch
    return f"{current_parts[0]}.{current_parts[1]}.{current_parts[2] + 1}"


def main() -> None:
    """Main entry point."""
    package_name = "unifiedui-sdk"
    
    floor = get_floor_version()
    current = get_pypi_version(package_name)
    next_version = calculate_next_version(floor, current)
    
    print(f"Floor version (pyproject.toml): {floor}")
    print(f"Current version (PyPI): {current or 'not published'}")
    print(f"Next version: {next_version}")
    
    # Output for GitHub Actions
    if len(sys.argv) > 1 and sys.argv[1] == "--output":
        print(f"\n::set-output name=version::{next_version}")


if __name__ == "__main__":
    main()
```

### 4.2 GitHub Actions Workflow

Datei: `.github/workflows/cd-pypi-release.yml`

```yaml
name: CD — PyPI Release

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      dry_run:
        description: "Dry run (don't publish)"
        required: false
        default: "false"
        type: boolean

permissions:
  contents: write  # For creating tags
  id-token: write  # For PyPI trusted publishing

jobs:
  release:
    name: Build & Release
    runs-on: ubuntu-latest
    # Prevent duplicate runs from merge commits
    if: github.event_name == 'workflow_dispatch' || !contains(github.event.head_commit.message, '[skip ci]')
    
    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0  # Full history for tags

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Set up Python
        run: uv python install

      - name: Calculate next version
        id: version
        run: |
          FLOOR=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
          
          # Query PyPI for current version
          CURRENT=$(curl -s https://pypi.org/pypi/unifiedui-sdk/json 2>/dev/null | python -c "import sys, json; d=json.load(sys.stdin); print(d['info']['version'])" 2>/dev/null || echo "")
          
          echo "floor=$FLOOR" >> $GITHUB_OUTPUT
          echo "current=$CURRENT" >> $GITHUB_OUTPUT
          
          # Calculate next version
          python << 'EOF'
          import os
          import re
          
          floor = os.environ.get('FLOOR', '0.1.0')
          current = os.environ.get('CURRENT', '')
          
          def parse(v):
              m = re.match(r'(\d+)\.(\d+)\.(\d+)', v)
              return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)
          
          if not current:
              next_ver = floor
          else:
              f = parse(floor)
              c = parse(current)
              if (f[0], f[1]) > (c[0], c[1]):
                  next_ver = floor
              else:
                  next_ver = f"{c[0]}.{c[1]}.{c[2] + 1}"
          
          with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
              f.write(f"version={next_ver}\n")
          
          print(f"Floor: {floor}, Current: {current or 'N/A'}, Next: {next_ver}")
          EOF
        env:
          FLOOR: ${{ steps.version.outputs.floor }}
          CURRENT: ${{ steps.version.outputs.current }}

      - name: Check if version already exists
        id: check
        run: |
          if git tag -l "v${{ steps.version.outputs.version }}" | grep -q .; then
            echo "exists=true" >> $GITHUB_OUTPUT
            echo "⚠️ Tag v${{ steps.version.outputs.version }} already exists"
          else
            echo "exists=false" >> $GITHUB_OUTPUT
            echo "✅ Tag v${{ steps.version.outputs.version }} will be created"
          fi

      - name: Update version in pyproject.toml
        if: steps.check.outputs.exists == 'false'
        run: |
          VERSION="${{ steps.version.outputs.version }}"
          sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
          echo "Updated pyproject.toml to version $VERSION"

      - name: Build package
        if: steps.check.outputs.exists == 'false'
        run: uv build

      - name: Create Git tag
        if: steps.check.outputs.exists == 'false' && github.event.inputs.dry_run != 'true'
        run: |
          VERSION="${{ steps.version.outputs.version }}"
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git tag -a "v$VERSION" -m "Release v$VERSION"
          git push origin "v$VERSION"

      - name: Publish to PyPI
        if: steps.check.outputs.exists == 'false' && github.event.inputs.dry_run != 'true'
        uses: pypa/gh-action-pypi-publish@release/v1
        # Uses trusted publishing (OIDC) - no API token needed
        # Configure at: https://pypi.org/manage/project/unifiedui-sdk/settings/publishing/

      - name: Summary
        run: |
          echo "## Release Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Property | Value |" >> $GITHUB_STEP_SUMMARY
          echo "|----------|-------|" >> $GITHUB_STEP_SUMMARY
          echo "| Floor Version | ${{ steps.version.outputs.floor }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Previous Version | ${{ steps.version.outputs.current || 'N/A' }} |" >> $GITHUB_STEP_SUMMARY
          echo "| New Version | ${{ steps.version.outputs.version }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Tag Exists | ${{ steps.check.outputs.exists }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Dry Run | ${{ github.event.inputs.dry_run || 'false' }} |" >> $GITHUB_STEP_SUMMARY
```

### 4.3 PyPI Trusted Publishing Setup

1. Gehe zu https://pypi.org/manage/project/unifiedui-sdk/settings/publishing/
2. Füge hinzu:
   - **Owner**: `unified-ui` (oder dein GitHub Username/Org)
   - **Repository**: `unifiedui-sdk`
   - **Workflow name**: `cd-pypi-release.yml`
   - **Environment**: (leer lassen)

---

## 5. Entwickler-Workflow

### Neues Patch-Release (automatisch)

```bash
# 1. Feature-Branch erstellen
git checkout -b feat/new-feature

# 2. Changes machen & committen
git add .
git commit -m "feat(tracing): add new span type"

# 3. PR erstellen & mergen
gh pr create --fill
gh pr merge --squash

# 4. Automatisch: CD erstellt Tag & deployed zu PyPI
#    (z.B. v0.1.5 → v0.1.6)
```

### Neues Minor-Release

```bash
# 1. pyproject.toml updaten
sed -i 's/version = "0.1.0"/version = "0.2.0"/' pyproject.toml

# 2. Commit & PR
git checkout -b feat/bump-minor
git commit -am "chore: bump version to 0.2.0"
gh pr create --fill --title "chore: prepare v0.2.0 release"
gh pr merge --squash

# 3. Automatisch: CD erstellt v0.2.0 Tag & deployed
```

### Neues Major-Release

```bash
# 1. pyproject.toml updaten
sed -i 's/version = "0.2.0"/version = "1.0.0"/' pyproject.toml

# 2. CHANGELOG.md updaten (Breaking Changes dokumentieren)
# 3. Commit & PR
git checkout -b feat/v1-release
git commit -am "chore: prepare v1.0.0 release"
gh pr create --fill --title "chore: prepare v1.0.0 release"
gh pr merge --squash

# 4. Automatisch: CD erstellt v1.0.0 Tag & deployed
```

---

## 6. Sicherheitsüberlegungen

### Trusted Publishing (OIDC)

- **Kein API-Token nötig**: GitHub Actions authentifiziert sich via OIDC
- **Keine Secrets zu managen**: Weniger Angriffsfläche
- **Workflow-gebunden**: Nur der definierte Workflow kann publishen

### Branch Protection

```yaml
# Empfohlene Branch Protection Rules für main:
- Require pull request reviews: 1
- Require status checks: 
  - lint
  - type-check
  - test
- Require branches to be up to date
- Include administrators
```

### Commit Signing (Optional)

```yaml
# In cd-pypi-release.yml hinzufügen:
- name: Import GPG key
  uses: crazy-max/ghaction-import-gpg@v6
  with:
    gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
    git_user_signingkey: true
    git_commit_gpgsign: true
    git_tag_gpgsign: true
```

---

## 7. Rollback-Strategie

### PyPI Yank (Soft-Delete)

```bash
# Version als "yanked" markieren (nicht mehr installierbar via pip)
# Muss über PyPI Web-Interface erfolgen
# https://pypi.org/manage/project/unifiedui-sdk/releases/
```

### Hotfix-Workflow

```bash
# 1. Hotfix-Branch von main
git checkout main
git pull
git checkout -b fix/critical-bug

# 2. Fix anwenden
git commit -am "fix(agents): resolve critical issue"

# 3. PR erstellen (wird automatisch deployed)
gh pr create --fill --title "fix: critical bug in agents"
gh pr merge --squash
```

---

## 8. Monitoring & Notifications

### GitHub Actions Status

```yaml
# Optional: Slack/Discord Notification hinzufügen
- name: Notify on success
  if: success()
  uses: 8398a7/action-slack@v3
  with:
    status: success
    fields: repo,message,commit,author,action,eventName,ref,workflow
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### PyPI Release Webhook

PyPI kann Webhooks an Discord/Slack senden:
- https://pypi.org/manage/project/unifiedui-sdk/settings/webhooks/

---

## 9. Alternativen (Nicht gewählt)

### Conventional Commits + semantic-release

```yaml
# Automatische Versionierung basierend auf Commit-Messages
# feat: → minor bump
# fix: → patch bump
# BREAKING CHANGE: → major bump
```

**Nicht gewählt weil:**
- Komplexere Setup (Node.js Dependency)
- Weniger Kontrolle über Major/Minor
- Erfordert strikte Commit-Message-Disziplin

### CalVer (Calendar Versioning)

```
# Version basierend auf Datum: 2026.03.08
```

**Nicht gewählt weil:**
- Nicht kompatibel mit SemVer-Erwartungen
- Unüblich für SDKs

---

## 10. Entscheidung

**Gewählte Option:** A (Floor-Based Auto-Versioning)

**Rationale:**
1. Automatisierung reduziert manuellen Aufwand
2. Floor-Konzept erlaubt kontrollierte Major/Minor-Bumps
3. Patch-Inkrementierung ist vorhersagbar
4. Trusted Publishing erhöht Sicherheit

---

## Anhang

### Checkliste für Ersteinrichtung

- [ ] PyPI Trusted Publishing konfigurieren
- [ ] `.github/workflows/cd-pypi-release.yml` erstellen
- [ ] `scripts/calculate_version.py` erstellen (optional, für lokales Testen)
- [ ] Branch Protection Rules aktivieren
- [ ] Erstes Release manuell erstellen (falls noch keine PyPI-Version existiert)

### Referenzen

- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [Semantic Versioning](https://semver.org/)
- [uv Build](https://docs.astral.sh/uv/guides/package/)
