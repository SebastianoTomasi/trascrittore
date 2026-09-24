# Security

## Boundary

**Owns:** Security policy and control requirements.

**Includes:** Authentication policy, authorization policy, data protection in
transit and at rest, retention and disposal controls, and security
requirements that components must enforce. These are representative, not
exhaustive.

**Excludes:** Actors, subjects, data classes, privacy and legal obligations,
owned by Product; trust boundaries and the component that enforces a control,
owned by Architecture; and concrete control mechanics or libraries, owned by
Implementation or Stack.

**Scope:** Shared rules live in `docs/security/`; decisions applying only
to one feature live in `docs/features/<feature-slug>/security/` and link to
shared rules instead of copying them. Security has no phase of its own.
Screening in the [Product](../product/advisor-product-feature.md) and
[Architecture](../architecture/advisor-architecture-feature.md)
catalogs can trigger either scope; a direct decision within this boundary can
also start an artifact. Create the feature folder only when writing its first
artifact, never as an empty phase placeholder.

The demand-driven questions below serve both scopes. Read only the questions
the trigger makes relevant; accept the artifact against that need and its own
decisions, without requiring the unused catalog to be exhausted.

## How this authority develops

The Product screening exposes a new actor, subject, or data class; the
Architecture screening exposes a new trust-boundary crossing. Resolve the owning
Product or Architecture answer first, then follow only the control path the
trigger makes necessary:

1. **Establish identity** — answer `security-authentication` when the system
   needs a shared way to recognize an actor or caller.
2. **Establish permission** — answer `security-authorization` when recognized
   parties must be allowed different actions or access to different subjects.
3. **Protect the data lifecycle** — answer `security-data-protection` when a
   declared data class needs controls in transit, at rest, or through
   retention and disposal.

In compact form: **foundation trigger → identity → permission → data
protection**. This is a dependency path, not a requirement to invent all three
policies at the first trigger. Amend only the answers that have substance,
accept them once the triggered concern is covered, and resume the feature.

## Questions

**1. `security-authentication`**
How does an actor prove they are who they claim to be?

- *Decides:* what every component may assume about the identity it is handed.
- *Why it matters:* a component that authenticates on its own terms is a second
  answer to a question that admits one.

**2. `security-authorization`**
How is a permitted action told apart from a forbidden one, and where is that
decided?

- *Decides:* where the rule lives and therefore where it can be audited.
- *Why it matters:* authorization spread across call sites cannot be reviewed,
  and its gaps are found by whoever finds them first.

**3. `security-data-protection`**
How is each regulated class of data protected in transit and at rest, and how
long is it kept?

- *Decides:* the controls that follow from the obligations Product declared.
- *Why it matters:* retention and encryption decided after storage exists means
  migrating data that was already held wrongly.
