# ADR Format

Store ADRs in `docs/adr/` using a four-digit sequential number and a lowercase kebab-case slug:

```text
0001-short-decision-title.md
0002-another-decision.md
```

Create `docs/adr/` only when the first qualifying ADR is needed.

## Minimal template

```md
# {Short decision title}

{In one to three sentences, state the relevant context, the decision, and why it was chosen.}
```

An ADR may contain only this paragraph. Its purpose is to preserve what was decided and why, not to satisfy a fixed section structure.

## Optional sections

Add a section only when omitting it would discard information useful to future readers.

### Status

Use frontmatter when the decision lifecycle needs to be tracked:

```yaml
---
status: accepted
---
```

Allowed statuses:

* `proposed`
* `accepted`
* `deprecated`
* `superseded`

When an ADR is superseded, identify its replacement:

```yaml
---
status: superseded
superseded_by: ADR-0007
---
```

### Considered Options

Include only when credible rejected alternatives and their rejection reasons are worth preserving.

### Consequences

Include only when the decision creates non-obvious effects, constraints, obligations, or risks.

### Sources

Link the material that informed the decision, with the relevant passage and
version or date when available, and briefly say what it contributed. A source
is informative: the current normative artifact states the project rule in its
own words. Changing or removing the source does not automatically change that
rule or the ADR's decision.

## Numbering

Before creating an ADR:

1. Scan `docs/adr/` for filenames beginning with a four-digit number.
2. Find the highest existing number.
3. Increment it by one, preserving four-digit zero padding.
4. Start with `0001` when no ADR exists.

Do not renumber existing ADRs.

## Superseding decisions

When a new ADR replaces an existing one:

* mark the old ADR as `superseded`;
* set its `superseded_by` field to the new ADR;
* reference the replaced ADR in the new decision.

## When to create or offer an ADR

All three conditions must be true:

1. **Hard to reverse:** changing the decision later would have a meaningful cost.
2. **Surprising without context:** a future reader would reasonably ask why it was chosen.
3. **Trade-off driven:** credible alternatives existed and one was selected for specific reasons.

If any condition is absent, do not create or offer an ADR.

Routine implementation details, obvious defaults, and easily reversible choices do not qualify.

## Typical qualifying decisions

* **Architectural shape:** choosing a monorepo or separating event-sourced writes from projected reads.
* **Integration between contexts:** using domain events instead of synchronous HTTP.
* **Technology choices with lock-in:** selecting a database, message bus, authentication provider, or deployment target that would be costly to replace.
* **Boundary and scope decisions:** assigning ownership and recording explicit exclusions.
* **Deliberate deviations from an obvious default:** preserving why the expected approach was rejected.
* **Decisions driven by constraints not visible in code:** choosing an approach because of compliance restrictions, external latency requirements, or similar constraints.
