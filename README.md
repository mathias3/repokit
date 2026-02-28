# repokit

Minimal CLI to scaffold and search context-first repositories for agent/data/ml work.

## Why

`repokit` helps you bootstrap repository documentation and keep agent context lightweight:
- scaffold new repositories from templates (`agent`, `ml`, `data`, `app`, `automation`)
- enforce a canonical `AGENTS.md` pattern with thin wrappers
- search markdown knowledge across repositories without loading full context

## Install (editable)

```bash
pip install -e .
```

## Commands

### Create new repo scaffold

```bash
repokit new "Sales Loss Forecasting" --type ml --destination /home/maciej/projects --format json
```

### Search markdown context

```bash
repokit search "redshift safety" --scope /home/maciej/projects --format json
```

### List repokit-managed repositories

```bash
repokit list --scope /home/maciej/projects --format json
```

### Show layered document status for one repository

```bash
repokit info /home/maciej/projects/Index_task --format json
```

### Check scaffold drift (missing/unexpected files)

```bash
repokit sync /home/maciej/projects/Index_task --format json
```

## Output formats

All commands support:

```bash
--format table|json|md
```

Default is `table`.

## Stable JSON envelope

Every command in `--format json` returns:

```json
{
  "ok": true,
  "command": "search",
  "exit_code": 0,
  "data": {}
}
```

Error responses use:

```json
{
  "ok": false,
  "command": "search",
  "exit_code": 3,
  "error": {
    "code": "no_matches",
    "message": "No matches found."
  }
}
```

## Exit codes

- `0`: success
- `1`: runtime/internal error
- `2`: invalid input/arguments
- `3`: not found / no results

## Template strategy

Shared templates are in `repokit/templates/_shared/`:
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `AMP.md`, `WINDSURF.md`
- `.windsurf/rules/safety.md`
- `.gitignore`, `CHANGELOG.md`

Type-specific templates are in:
- `repokit/templates/agent/`
- `repokit/templates/ml/`
- `repokit/templates/data/`
- `repokit/templates/app/`
- `repokit/templates/automation/`

## Test

```bash
pytest -q
```

## Recipes

Ready-to-run pipelines:

- `recipes/context-audit/pipeline.sh`
- `recipes/scaffold-check/pipeline.sh`
