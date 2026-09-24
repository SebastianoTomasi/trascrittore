# `CONTEXT.md` Format

`CONTEXT.md` defines the canonical domain language of a bounded context. Keep it implementation-independent: it is a glossary, not a specification, architecture document, or scratchpad.

## Single-context format

```md
# {Context Name}

{In one or two sentences, describe the domain responsibility of this context and why it exists.}

## Language

**Order**  
{Define the concept in one or two sentences and distinguish it from nearby concepts when necessary.}  
_Avoid_: Purchase, transaction

**Invoice**  
A request for payment issued to a customer for delivered goods or services.  
_Avoid_: Bill, payment request

**Customer**  
A person or organization that places an order.  
_Avoid_: Client, buyer, account
```

Use `_Avoid_` only when alternative terms are likely to cause ambiguity or conflict with the chosen ubiquitous language. Omit it when no meaningful alternatives exist.

## Glossary rules

* **Choose one canonical term.** When several terms refer to the same concept within the context, select one and list confusing alternatives under `_Avoid_`.
* **Define concepts precisely.** State what distinguishes the concept in this domain. Include relevant responsibilities or boundaries only when needed to separate it from related concepts.
* **Keep definitions concise.** Use one or two sentences unless a longer definition is necessary to remove material ambiguity.
* **Use domain language only.** Exclude general programming, infrastructure, framework, database, and user-interface terminology.
* **Record resolved language only.** Do not add open questions, tentative definitions, implementation notes, requirements, or decision history.
* **Keep terms context-local.** The same word may have different meanings in different bounded contexts; define it independently in each relevant `CONTEXT.md`.
* **Avoid circular definitions.** Do not define one term solely through another undefined term.
* **Group only when useful.** Add descriptive `###` subheadings when stable, meaningful clusters emerge. Otherwise retain a flat list.
* **Preserve established order.** When updating an existing glossary, follow its current ordering convention. For a new glossary, use an order that makes related terms easy to understand.

Before adding a term, verify that it represents a project-specific domain concept rather than a general technical concept.

## Repository structures

### Single bounded context

Use one `CONTEXT.md` at the repository root:

```text
/
├── CONTEXT.md
├── docs/
└── src/
```

### Multiple bounded contexts

If `/CONTEXT-MAP.md` exists, use it to locate each bounded context and its glossary:

```text
/
├── CONTEXT-MAP.md
└── src/
    ├── ordering/
    │   └── CONTEXT.md
    ├── billing/
    │   └── CONTEXT.md
    └── fulfillment/
        └── CONTEXT.md
```

Use this format for the map:

```md
# Context Map

## Contexts

- [Ordering](./src/ordering/CONTEXT.md) — receives and tracks customer orders
- [Billing](./src/billing/CONTEXT.md) — manages charges, invoices, and payments
- [Fulfillment](./src/fulfillment/CONTEXT.md) — manages picking, packing, and shipping

## Relationships

- **Ordering → Fulfillment**: communicates that an order is ready for fulfillment.
- **Fulfillment → Billing**: communicates that goods or services have been delivered and may be invoiced.
- **Ordering ↔ Billing**: coordinate through explicitly defined customer and order references.
```

Describe relationships in domain terms. Include technical mechanisms—such as events, APIs, shared kernels, or shared types—only when they are part of an established cross-context contract and materially clarify the relationship.

Do not imply that two contexts share the same model merely because they use similar terminology.

## Selecting the applicable structure

1. If `/CONTEXT-MAP.md` exists, treat the repository as multi-context and use it to locate the relevant `CONTEXT.md`.
2. Otherwise, if `/CONTEXT.md` exists, treat the repository as single-context.
3. If neither file exists, create `/CONTEXT.md` only when the first domain term is resolved.
4. In a multi-context repository, update the context that owns the concept. Ask the user only when ownership cannot be determined reliably from the map, code, documentation, or conversation.
5. Create a new bounded context or modify `CONTEXT-MAP.md` only when the context boundary itself has been explicitly resolved.
