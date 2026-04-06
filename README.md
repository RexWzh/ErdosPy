# erdospy

`erdospy` is a Python package and CLI for exploring Paul Erdős problems from a bundled SQLite snapshot.

Current Phase 1 scope:

- standard `src` layout package
- reusable SQLite query layer
- `typer + rich` CLI for core read workflows

## Install

```bash
pip install -e .
```

## CLI

```bash
erdospy stats
erdospy get 42
erdospy get 42 --json
erdospy get 42 --comments
erdospy search "Sidon set"
erdospy list --status open --tag primes --has-prize
```
