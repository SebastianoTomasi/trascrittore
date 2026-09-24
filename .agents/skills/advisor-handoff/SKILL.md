---
name: advisor-handoff
description: Create a temporary conversation-transfer handoff under docs/handoffs/ for a fresh session. Use only when the user explicitly requests this skill, not for deferred work or automatic session recovery.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

Write a handoff document that compacts the current conversation so a fresh
session can continue the work. Save it as
`docs/handoffs/<descriptive-focus>-handoff.md`, choosing a concise lowercase
kebab-case focus. Never overwrite an existing entry; if the chosen path is
occupied, choose another concise descriptive name.

Tailor the document to the user's stated next-session focus, or to the active
work when no argument was provided. Use a flexible layout that includes at
least:

- the next objective;
- the current state;
- settled decisions and constraints;
- authoritative file, commit, or diff references;
- the next action;
- open questions.

Reference persisted artifacts instead of copying their contents. Redact
sensitive information such as credentials, secrets, and personally identifiable
information.

Create one new file only. Do not inventory, discover, prioritize, resume,
archive, mark, or delete handoffs; checking whether the chosen destination is
occupied is not lifecycle management. A fresh session reads only the handoff
the user identifies, and cleanup remains manual.
