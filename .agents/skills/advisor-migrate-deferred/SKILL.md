---
name: advisor-migrate-deferred
description: Migrate legacy open docs/deferred Markdown records into the project's configured issue tracker when the user explicitly requests migration. Preserve their context, avoid duplicate issues, repair references, and remove each source only after verification. Do not use for ordinary deferred-work capture or recovery.
---

# Migrate legacy deferred records

This is an explicitly requested, one-time transfer of project work records,
not part of initialization or normal advisor recovery. Migrate only selected
`State: open` files from `docs/deferred/`; leave `closed` files and unselected
files untouched. Do not run this skill merely because an old directory exists.

## Establish the target and inventory

1. Read the target project's `advisor-agents.md` and its relevant project
   instructions. Read `docs/agents/issue-tracker.md` and
   `docs/agents/triage-labels.md` before using the tracker. If either is
   missing, ask for the tracker setup and stop; do not guess a destination.
   Follow the configured tracker operations, not a hard-coded GitHub workflow.
   Check that the installed advisor's normal deferred-work procedure already
   recovers open `advisor:deferred` issues from that tracker. If it still reads
   only `docs/deferred/`, stop: transferring and removing sources would make
   the work disappear from ordinary advisor sessions.
2. Inventory the selected records by title and opening fields. Read every
   selected open record in full, including progress, questions, resolutions,
   and links. Treat an unreadable record or an unknown state as blocked, not
   empty. Read linked material needed to understand whether it describes the
   same work; a link alone is not another migration input.
3. Check the tracker's `advisor:deferred` routing label. If absent, add it as
   an advisor-specific axis in the project's label configuration and provision
   it in the tracker, preserving the configured category and triage labels.
   Stop if the configuration and tracker cannot be made consistent. Do not
   apply `ready-for-agent` merely because a record is open or ready to revisit.

## Map each record to an issue

For each source, search both open and closed issues for its title, linked issue
identifiers, and the stable `Migrated from: docs/deferred/<filename>` marker.
Read candidate bodies, labels, and comments before choosing:

- **Same work:** enrich the existing issue with missing deferred context and
  add `advisor:deferred`. Preserve its current title, other labels, state,
  comments, and useful content. If it is closed while the source is open,
  resolve the conflict with the user before changing its state.
- **Related but distinct work:** create a new issue and link the related issue.
  A record mentioning an issue does not prove they are the same work. When a
  record mentions several issues, assess each rather than merging them.
- **No existing issue:** create one open issue with `advisor:deferred`.
- **Ambiguous match or conflicting instructions:** ask one focused question;
  continue independent records while that one waits.

An implementation ticket from `to-tickets` is not automatically the same
record as a deferred decision about that implementation. Preserve that
distinction when choosing whether to enrich it or create a related issue.

The issue must preserve the record's question or intended outcome, Scope,
Destination, Revisit when, why it waited, accepted constraints, relevant
links, partial progress, and remaining questions. Keep the original title
where it remains accurate. Add the plain-text source marker above to every
created or enriched issue so a retry finds it after the file is removed. Do
not turn an undecided field into an invented answer or add implementation
acceptance criteria to a decision issue.

For a local Markdown tracker, use one file per advisor issue under
`.scratch/advisor-deferred/issues/`, apart from `to-tickets`'s numbered feature
ticket sets. Represent the routing label, open state, Scope, Destination, and
Revisit when in the file; use the configured tracker convention for comments.
Do not use a triage `Status` value to stand for open/closed or inferred
readiness. If the configured local convention conflicts with this layout,
surface the conflict before writing.

## Preserve links and finish one record at a time

Resolve every relative link from the original file's directory. In a hosted
issue, turn links to retained repository files into working repository URLs;
links to other records being migrated must point to their verified issues.
In a local issue, rewrite relative paths from its new directory. Preserve
heading-specific references where they carry meaning. If a target is missing,
private, or only present in uncommitted local work, preserve the needed fact in
the issue or leave this record blocked; never silently drop the link.
For records linking to one another, identify and verify all their issue
targets before rewriting those links or deleting any of their source files.

Find references **to** the source file before deletion, including links from
other deferred records and normative artifacts. Repoint references in
in-scope editable files to the verified issue without changing the surrounding
decision. A closed legacy record remains untouched: if it points to a source
slated for deletion, leave that source blocked and ask whether the closed
record may be amended. If the referent's meaning changes, use
`advisor-propagate-change`; a link repair alone is a focused edit. Follow the
project's restrictions on reading handoffs or protected material. An
inaccessible inbound reference blocks source deletion until it can be
repaired or the user resolves it.

After writing one issue, read it back from the tracker and check its body,
label, open state, links, and source marker. Verify that every known inbound
reference now resolves, then remove that source file. If any check fails,
leave the file and report the partial issue write so a retry can reuse it.
Never delete a source merely because issue creation returned success. Do not
remove a directory containing closed or unmigrated records.

Report the issue identifier for each migrated record, whether it reused an
existing issue, which sources were removed, and every skipped or blocked file
with the specific reason. A rerun must inspect source markers and existing
issues before creating anything, and must not duplicate already transferred
work.
