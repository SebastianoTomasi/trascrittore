# Delivering the agent skill

**Status:** accepted

## Scope

This artifact states how the agent skill reaches a PC and stays in step with the
transcriber's image. What the skill describes is in
[the architecture](../architecture/agent-cli-architecture.md#components). How
the image itself is built and exported is left to `docker/build.ps1` and
`docker/Installa.bat`.

## Dependencies

- [Components](../architecture/agent-cli-architecture.md#components) — the
  skill describes the launcher's commands, so a skill from another version
  would describe commands that do not exist.
- [Agents](../../../product/transcriber-promise.md#agents) — the promise names
  Claude Code and Codex, so the skill is installed for both.

## Rules

- **Part of every release.** `build.ps1 -Export` writes the skill next to the
  image and the other files a person downloads.
- **Installed with the image.** Every time `Installa.bat` installs the image, it
  also installs the skill, named `trascrittore`, for each agent at user level:
  - Claude Code under `%USERPROFILE%\.claude\skills\`;
  - Codex under `%USERPROFILE%\.agents\skills\`, its user-level skills folder.

  The skill replaces the previous version, and it works in whatever folder the
  person opens their agent.
- **Tied to the transcriber's folder.** The installed skill names the folder
  where the transcriber was installed, since its commands run the launcher
  there. When the person moves that folder, they run `Installa.bat` again, as
  `LEGGIMI.md` tells them.
- **Same version.** The skill never ships separately from the image. It
  describes only the commands of the image it came with.
- **A fallback.** The launcher's help text stays complete, so an agent without
  the skill can still find out how to use the commands.
- **The guide tells the person.** `LEGGIMI.md` says that installing also
  installs the skill for Claude Code and Codex, and gives an example of what to
  ask the agent.

## Later

If the private registry in
[the deferred item](../../../deferred/transcriber-image-registry.md) is
adopted, the skill follows the image on the same delivery path.
