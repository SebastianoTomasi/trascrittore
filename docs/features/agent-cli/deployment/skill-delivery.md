# Delivering the agent skills

**Status:** accepted

## Scope

This artifact states how the agent skills reach a PC and stay in step with the
transcriber's image. What they describe is in
[the architecture](../architecture/agent-cli-architecture.md#components). How
the image itself is built and exported is left to `docker/build.ps1` and
`docker/Installa.bat`.

## Dependencies

- [Components](../architecture/agent-cli-architecture.md#components) — the
  `trascrittore` skill describes the launcher's commands, and both skills run
  the image's ffmpeg for a video's frames, so a skill from another version
  would describe commands or an image that do not exist.
- [Agents](../../../product/transcriber-promise.md#agents) — the promise names
  Claude Code and Codex, so the skills are installed for both.
- [Non-goals](../../../product/transcriber-promise.md#non-goals) — correcting
  misheard words is the agent's work on the text, so the transcriber delivers
  the `fix-transcript` skill and nothing else for it.

## Rules

- **Part of every release.** `build.ps1 -Export` writes the skills next to the
  image and the other files a person downloads.
- **Installed with the image.** Every time `Installa.bat` installs the image, it
  also installs the skills `trascrittore` and `fix-transcript` for each agent
  at user level:
  - Claude Code under `%USERPROFILE%\.claude\skills\`;
  - Codex under `%USERPROFILE%\.agents\skills\`, its user-level skills folder.

  Each skill replaces its previous version, and they work in whatever folder
  the person opens their agent.
- **Tied to the transcriber's folder.** The installed `trascrittore` skill
  names the folder where the transcriber was installed, since its commands run
  the launcher there. When the person moves that folder, they run
  `Installa.bat` again, as `LEGGIMI.md` tells them.
- **Same version.** The skills never ship separately from the image. The
  `trascrittore` skill describes only the commands of the image it came with.
- **A fallback.** The launcher's help text stays complete, so an agent without
  the `trascrittore` skill can still find out how to use the commands.
- **The guide tells the person.** `LEGGIMI.md` says that installing also
  installs the skills for Claude Code and Codex, and gives an example of what to
  ask the agent with each.

## Later

If the private registry in
[the deferred item](../../../deferred/transcriber-image-registry.md) is
adopted, the skills follow the image on the same delivery path.
