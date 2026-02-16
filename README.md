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
repokit new "Sales Loss Forecasting" --type ml --destination /home/maciej/projects
```

### Search markdown context

```bash
repokit search "redshift safety" --scope /home/maciej/projects
```

### List repokit-managed repositories

```bash
repokit list --scope /home/maciej/projects
```

### Show layered document status for one repository

```bash
repokit info /home/maciej/projects/Index_task
```

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
