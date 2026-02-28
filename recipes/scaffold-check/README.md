# Scaffold Check Recipe

This pipeline validates one repository against repokit templates.

## Usage

```bash
bash recipes/scaffold-check/pipeline.sh /home/maciej/projects/my-repo ./out/scaffold-check
```

## Artifacts

- `info.json`: layered document status from `repokit info`
- `sync.json`: drift report from `repokit sync`

Each artifact follows the stable JSON envelope returned by CLI commands.
