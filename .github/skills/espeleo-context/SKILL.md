---
name: espeleo-context
description: Read and navigate the eSpeleoSociety codebase with minimal token cost using lean-ctx and the free graphify AST code graph. Use at the start of any non-trivial task in this repository, when exploring unfamiliar code, when asked "ako to funguje", "kde sa to deje", "najdi", "co sa rozbije ked zmenim X", or when the context window is filling up.
---

# eSpeleoSociety Context Skill

This repository is small in file count but heavy in a few files: `db.py` is
1232 lines, `utils.py` ~746, `backend/repository.py` 564, plus large dialogs and
views. Reading them naively burns the context window before any work starts.
`utils.py`, `db.py` and `main.py` are the import hotspots — almost everything
depends on them.

## Rule: never `cat` a large file in this repo

Use `lean-ctx` `ctx_read` with the mode that matches your intent:

| Intent | Mode |
|---|---|
| Understand a module's API without its bodies | `signatures` |
| See what a module depends on and exports | `map` |
| You are about to edit the file | `anchored` |
| Only the lines relevant to a task | `task` |
| A specific known range | `lines:N-M` |

Reading `db.py`, `utils.py`, `main.py`, `backend/app.py` and
`backend/repository.py` in `map` mode costs a few hundred tokens instead of tens
of thousands. In practice this saves 85-90% on exploration reads in this
repository.

For "what breaks if I change this file" use `ctx_impact`; for "who calls this
function" use `ctx_callgraph`. Do not reconstruct either by grepping.

## The free code graph

`graphify` is installed and the graph for this repository is already built:

```bash
graphify update .        # rebuild, AST only, no LLM, zero token cost
```

Verified: 123 files, 593 nodes, 566 edges, 30 communities, **0 input / 0 output
tokens**. Output goes to `graphify-out/`, which is already in `.gitignore`.

Query it instead of reading files:

```bash
graphify query "how is the ecp card issued and uploaded" --budget 900
graphify path "ecp_issuance" "ftp_uploader"
graphify explain "DatabaseManager"
```

Rebuild after any significant refactor and note that the report records the
commit it was built from, so you can tell when it is stale:

```bash
grep "Built from commit" graphify-out/GRAPH_REPORT.md && git rev-parse --short HEAD
```

### Honest limitations of the current graph

- **Cross-file import resolution is disabled** on this machine: the installed
  `graphify` 0.7.10 expects tree-sitter language ABI 13-14 while the installed
  tree-sitter core is version 15, so it prints
  `Cross-file import resolution failed, skipping`. The graph therefore has
  in-file structure but weak cross-module edges. For cross-module questions
  prefer `ctx_impact` / `ctx_callgraph`, which are unaffected. To fix it, pin a
  compatible `tree-sitter` for the interpreter that runs `graphify`, or upgrade
  `graphifyy` once a release supporting ABI 15 is available.
- **Communities and nodes are unlabeled** because semantic extraction was not
  run — that step uses an LLM and does cost tokens. `graphify query` currently
  ranks Markdown nodes from `fix.md` and `docs/superpowers/plans/` highly, so
  code questions can return documentation noise. If you want the labeled
  semantic graph, run the full `/graphify` pipeline once; results are cached per
  file, so later `--update` runs only re-extract what changed.
- `docs/superpowers/plans/` contains outdated June 2026 plans that pollute
  query results. Treat any hit from that folder as historical, not current.

## Order of operations for a new task

1. `graphify query "<question>" --budget 1200` — cheap orientation.
2. `ctx_read` in `map` / `signatures` mode on the 2-4 files that came back.
3. `ctx_impact` on any file you intend to change.
4. `ctx_read` in `anchored` mode only on the files you actually edit.
5. Verify with `espeleo-preflight`.

## Keeping the session small

- Prefer targeted `unittest` module runs over the full discover run while
  iterating; the full suite is only ~2 seconds, but its verbose output is not.
- Pipe noisy commands through `tail`/`head` rather than dumping full output.
- The generated artifacts in `graphify-out/` and `build/` are gitignored — never
  read `graph.json` (400 KB) or `graph.html` (440 KB) directly into context; use
  `graphify query`.
- `lean-ctx` enforces a shell allowlist. If a command is blocked, allow it
  explicitly (`lean-ctx allow <cmd>`, already done for `graphify`) rather than
  disabling the gate.
