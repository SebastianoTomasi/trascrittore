---
name: advisor-domain-modeling
description: Build and refine a project's domain model. Use when defining domain terminology or ubiquitous language, resolving domain boundaries, writing or updating the glossary at CONTEXT.md or a decision record under docs/adr/, recording a qualifying architectural decision, or maintaining the domain model for another skill.
disable-model-invocation: false
---

# Domain Modeling

Actively refine the project’s domain model while designing. Challenge ambiguous or conflicting terminology, test relationships with concrete edge cases, and record resolved terms and qualifying decisions as soon as they are established.

Use this skill only when changing the domain model, not merely reading it for context.

## Repository structure

A repository with one bounded context typically uses:

```text
/
├── CONTEXT.md
├── docs/
│   └── adr/
└── src/
```

If `/CONTEXT-MAP.md` exists, treat the repository as multi-context. Read the map to locate each context’s glossary and ADR directory:

```text
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                 ← system-wide decisions
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/        ← context-specific decisions
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

Create files and directories only when needed:

* Create the relevant `CONTEXT.md` when the first term for that context is resolved.
* Create the relevant `docs/adr/` directory when the first qualifying ADR is written.

## Workflow

### Resolve terminology

When the user uses a term that conflicts with an existing glossary definition, surface the conflict immediately and ask which meaning is authoritative.

When a term is vague, overloaded, or conflates distinct concepts, propose precise canonical terminology and explain the distinction briefly.

### Test the model with scenarios

When discussing entities, relationships, states, or boundaries, introduce concrete scenarios—including relevant edge cases—to expose ambiguity and force precise definitions.

### Verify against the repository

Cross-reference domain claims with relevant code and documentation. Surface contradictions explicitly and ask which behavior or description is authoritative.

Do not silently change the domain model to match either source.

### Update the glossary immediately

As soon as a term is resolved, update the appropriate `CONTEXT.md` using [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md). Do not defer or batch glossary updates.

Keep every `CONTEXT.md` limited to domain terminology and definitions. Exclude implementation details, architectural decisions, specifications, unresolved notes, and scratch content.

In multi-context repositories, update the glossary belonging to the affected bounded context.

### Create ADRs sparingly

Create or offer an ADR only when the decision meets all three conditions:

1. **Hard to reverse:** changing it later would impose meaningful cost.
2. **Surprising without context:** a future reader would reasonably ask why it was chosen.
3. **Trade-off driven:** credible alternatives existed and the choice was made for specific reasons.

If any condition is absent, do not create an ADR.

Use [ADR-FORMAT.md](./ADR-FORMAT.md). Store system-wide ADRs in `/docs/adr/` and context-specific ADRs in that context’s `docs/adr/`.

An adopted repository keeps the ADR directory and numbering it already has.
Before writing or superseding an ADR, apply the provenance, dependency, and
review rules in `docs/advisor-docs.md`; read that file when it is not already
read. It owns those rules, and this skill does not restate them.
