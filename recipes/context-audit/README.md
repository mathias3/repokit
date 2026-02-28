# Context Audit Recipe

This pipeline produces two JSON artifacts for agent workflows:
- markdown search hits
- repokit-managed repositories in scope

## Usage

```bash
bash recipes/context-audit/pipeline.sh /home/maciej/projects ./out/context-audit "redshift safety"
```

## Output schema

Both files use stable CLI envelope:
- `ok` (bool)
- `command` (string)
- `exit_code` (int)
- `data` (object)
- `error` (object, only when `ok=false`)
