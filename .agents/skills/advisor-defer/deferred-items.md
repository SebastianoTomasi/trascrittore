# Deferred items

Keep durable future work in one Markdown file under the target project's
`docs/deferred/` directory. Deferred items are project work records, not
normative artifacts, conversation handoffs, or substitutes for accepted
prerequisites. No tracker is used.

## Capture

Accept a question, idea, or other future concern when it is not needed by the
current work. Before writing, make sure the input identifies what should be
revisited and gives either a possible outcome or a meaningful revisit
condition. If it does not, conduct a short `advisor-grill-me` session, one
decision-critical question at a time, only until that minimum is clear. Do not
save an unintelligible note.

Look for an existing record of the same work and update it; otherwise choose a
descriptive lowercase kebab-case filename. Initialization normally creates the
empty directory; if it is absent in an older or partial installation, create it
with the first real record. Keep filenames stable through routing changes and
closure. Advice alone reads records without creating or changing them.

Before choosing Scope or Destination, inspect current work when it can be
identified, and read the relevant authority boundary when assessing a candidate
destination. Use the conversation and project files to fill what they establish;
`undecided` is not a shortcut when available evidence can resolve the field.
Leave a field `undecided` when evidence is insufficient; do not explore
unrelated work solely to fill it.

Use this opening shape; the prose beneath it follows the future work:

```markdown
# Retry policy for payments

**State:** open
**Scope:** feature:checkout
**Destination:** architecture
**Revisit when:** the payment provider contract is being defined.

Decide which payment failures may be retried and how to avoid duplicate charges.
This can wait while Product settles how uncertain payment outcomes are shown.
Link the originating artifact and any already-established constraints here.
```

State is `open` or `closed`. Scope is `project`, `feature:<confirmed-slug>`, or
`undecided`. Destination is one of the project's authority names, or `undecided`;
use authority names also for work such as Security or Operations that has no
phase. Describe the revisit condition in plain language, linking specific
inputs where known. Use `undecided` for a condition still needing clarification.
For an undeclared feature, describe the intended capability in the body and
keep Scope undecided until its identity is agreed; create no feature folder.

The record must make sense without the original conversation: state what should
be revisited, why it can wait, and the relevant context, links, established
facts, partial progress, and remaining questions. An input needed by the
current artifact stays an open decision in that artifact. Do not turn a user's
choice to proceed against advice into a deferred item or deviation record.

A Product non-goal remains an authoritative Product decision and creates no
deferred item automatically. If there is actual future work to reconsider that
non-goal, link the Product rule rather than duplicating it.

## Recover and classify

Before recommending work or starting or resuming an advisor session:

1. List the records and read their titles and opening fields. If the directory
   is absent, continue normally. An unreadable record is an incomplete check,
   not evidence that no deferred item exists; name it in the result.
2. For a general next-work request, consider all open records. For scoped work,
   read relevant open records in full: the feature and authority, shared
   project work that may apply, and undecided routing that may concern it.
   Inspect incomplete fields as candidates for classification. Follow related
   subjects and links too, since a destination can be stale. Closed records
   need body reads only when linked or relevant to an apparent duplicate.
3. Compare each candidate with current accepted decisions and necessary inputs.
   Report items ready now, still waiting and what they await, and apparently
   answered or superseded items with evidence. Read previous progress before
   asking anything. A label, closed record, or phase name proves no prerequisite
   by itself. Do not store these judgements as additional states.
4. Present unclassified items for routing when it matters to the work. During
   an authorized session, update a destination inferable from the authority
   boundaries; ask only if the choice changes the intended scope. Advice alone
   returns the assessment without changing the record; the calling next-work
   workflow owns the recommendation. Consider relevant deferred items before
   dependent decisions and re-evaluate waiting ones as their inputs settle.
   The session workflow remains one question at a time.

## Resume and close

Keep partial progress and remaining questions in the open record so another
session can resume it. Write current rules in the owning artifact through the
normal acceptance and propagation procedure, then set State to `closed` and add
`## Resolution` linking the accepted answer. For an item already answered,
verify that the answer applies before closing. A deliberately dropped item
closes with the user's agreed reason; changes to accepted rules still propagate.

Keep the closed file at the same path. Link to the normative answer rather than
maintaining another copy of it. Closure is work tracking, not artifact
acceptance. Existing external issues are outside this local procedure.
