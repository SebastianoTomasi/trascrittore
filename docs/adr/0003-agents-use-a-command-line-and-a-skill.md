# Agents use a command line and a skill, not an MCP server

Agents reach the transcriber through commands that ask no questions and a skill
that tells them how to use those commands, not through an MCP server. Every
agent the transcriber serves can run commands, and a transcription lasts
minutes, which fits a command started in the background better than a tool
call that keeps waiting.

## Considered options

- **An MCP server** exposing transcription and naming as tools: it would also
  reach assistants without a shell, such as Claude Desktop or claude.ai, but it
  must be configured on each PC, and a tool call that waits for a transcription
  can time out, especially on a CPU, where a transcription can last longer than
  the recording.

## Consequences

- An assistant without a shell cannot use the transcriber.
- The skill must always match the commands of the installed version, so it
  ships with the image.
- If an assistant without a shell becomes a user, this decision is reopened.
