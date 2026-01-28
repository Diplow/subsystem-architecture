# Subsystem Architecture

A framework for organizing TypeScript codebases into subsystems with enforced architectural boundaries.

## What This Is

Subsystem Architecture turns directories into **subsystems** — self-documenting modules with explicit dependencies, public APIs via `index.ts`, and enforced import boundaries. It provides:

- **Architecture checker** — validates subsystem boundaries, import rules, and documentation requirements
- **Rule of 6 checker** — validates subsystem count, functions per file, function length, and argument count
- **Subsystem tree** — visualizes the full subsystem hierarchy with types and lines of code

Each subsystem is a directory containing a `dependencies.json` file that declares its type, allowed imports, and child subsystems.

## Quick Setup

### 1. Add as git submodule

```bash
git submodule add https://github.com/Diplow/subsystem-architecture.git scripts/checks/architecture
```

### 2. Add pnpm scripts to `package.json`

```json
{
  "scripts": {
    "check:architecture": "python3 -m scripts.checks.architecture.main",
    "check:ruleof6": "python3 -m scripts.checks.architecture.ruleof6.main",
    "subsystem-tree": "python3 -m scripts.checks.architecture.tree.main"
  }
}
```

All tools are invoked as Python modules directly — no wrapper scripts needed.

> **Note:** With `python3 -m`, pass args directly: `pnpm subsystem-tree -- src/lib/domains`.
> Named flags after `--` won't work (`pnpm subsystem-tree -- --format json`).
> If you need that, create a thin wrapper that strips the `--`

### 3. Create your first `dependencies.json`

At your source root (e.g. `src/`), create:

```json
{
  "type": "router",
  "allowed": [],
  "subsystems": ["./app", "./lib", "./server"]
}
```

Then run `pnpm check:architecture` to validate.

### 4. Copy the CLAUDE.md section below into your project

Copy the section between the markers into your project's `CLAUDE.md` to give AI agents the context they need to work with your subsystem architecture.

---

## For Your CLAUDE.md

Copy everything between the START and STOP markers below into your project's `CLAUDE.md`.

<!-- START CLAUDE.md template -->

### Subsystem Architecture

The codebase is organized into subsystems — directories containing a `dependencies.json` file. Each subsystem has:
- `dependencies.json` — declares allowed imports and subsystem type
- `index.ts` — public API (all external imports must go through this)
- `README.md` — mental model, responsibilities, child subsystems

**Architectural constraints** (enforced by `pnpm check:architecture`):
- Import only through a subsystem's `index.ts`, never reach into internals
- Only import dependencies declared in `dependencies.json`
- No cross-domain imports (domains are isolated)
- Subsystems exceeding 1000 LoC must have a `README.md`

**Discovery:**
```bash
pnpm subsystem-tree                          # ASCII tree with types and LoC
pnpm subsystem-tree -- --format json         # JSON output
pnpm subsystem-tree -- src/lib/domains       # Subtree only
```

#### Workflow: Feature Planning

1. Run `pnpm subsystem-tree` to map the landscape
2. Identify impacted subsystems, read each one's `README.md`
3. Structure the plan with one step per impacted subsystem
4. When delegating a step to a subagent (Task tool), include the subsystem's `README.md` content as context in the prompt
5. Check `index.ts` exports and `dependencies.json` before writing code
6. Consider whether new subsystems should be introduced (Rule of 6 exceeded, >1000 LoC, natural boundary)

#### Workflow: Impact Analysis

1. Read the changed subsystem's `index.ts` to see public surface
2. Grep for consumers: `grep -rn "from.*~/path/to/subsystem['\"]" src --include="*.ts" --include="*.tsx"` (reliable because architecture enforcement forces all imports through `index.ts`)
3. Group results by subsystem, check transitive impact

#### Workflow: New Subsystem Introduction

When to create: >6 files (Rule of 6), >1000 LoC, natural concern boundary.

Checklist:
1. Create `dependencies.json` with type and allowed dependencies
2. Create `index.ts` as the public API
3. Create `README.md` with mental model, responsibilities, and subsystems
4. Add to parent's `"subsystems"` array in its `dependencies.json`
5. Run `pnpm check:architecture` to validate

#### Rule of 6

The codebase follows the **Rule of 6** for consistent organization (enforced by `pnpm check:ruleof6`):

- **Subsystems**: Max 6 declared child subsystems per parent. Group related children into a router subsystem.
- **Files**: Max 6 functions per file. Move extras to other files. Prefix internal functions with `_`.
- **Functions**: Max 50 lines (warning), 100 lines (error). Refactor into max 6 function calls at the same abstraction level.
- **Arguments**: Max 6 arguments per function, or 1 object with max 6 keys at the same abstraction level.

Custom thresholds via `.ruleof6-exceptions` files:
```
# Function-specific: file:function:threshold
src/path/file.ts:complexFunction: 150  # Justification for exception

# File-specific: file:threshold
src/path/file.ts: 10  # Justification for exception
```

<!-- STOP CLAUDE.md template -->

---

## Architecture Philosophy

Subsystems enforce three core ideas:

1. **Explicit boundaries** — Every subsystem declares what it depends on (`dependencies.json`) and what it exposes (`index.ts`). No implicit coupling.

2. **Hierarchical encapsulation** — Child subsystems are only known within their parent. Siblings must use public APIs. This keeps the dependency graph shallow and navigable.

3. **Documentation as architecture** — Subsystems over 1000 LoC must have a `README.md`. The structure itself is the documentation — `pnpm subsystem-tree` gives you the map.

For detailed rules (subsystem types, dependency management, reexport boundaries, domain structure), see the [`rules/`](rules/) directory.

## Error Types

The checker produces structured JSON errors. Each error has a `type` field:

| Type | Description |
|------|-------------|
| `complexity` | Missing `dependencies.json` or `README.md` for large subsystems |
| `import_boundary` | Direct imports bypassing `index.ts` |
| `domain_import` | Services imported by non-API code |
| `domain_structure` | Invalid domain organization |
| `subsystem_structure` | Missing subsystem declarations in parent |
| `dependency_format` | Invalid path formats in `dependencies.json` |
| `redundancy` | Duplicate dependency declarations |
| `nonexistent_dependency` | Dependency pointing to non-existent path |
| `reexport_boundary` | Invalid reexports in `index.ts` |
| `file_conflict` | File/folder naming conflicts |
| `subsystem_count` | Too many child subsystems declared (Rule of 6) |
| `file_functions` | Too many functions per file (Rule of 6) |
| `function_lines` | Function exceeds line limit (Rule of 6) |
| `function_args` | Too many function arguments / object keys (Rule of 6) |

Architecture errors: `test-results/architecture-check.json`. Rule of 6 errors: `test-results/rule-of-6-check.json`.

Filter with `jq`:

```bash
jq '.errors[] | select(.type == "import_boundary")' test-results/architecture-check.json
jq '.summary' test-results/architecture-check.json
```

## Further Reading

- [README-STRUCTURE.md](README-STRUCTURE.md) — Template for subsystem READMEs
- [`rules/`](rules/) — Detailed rule implementations
