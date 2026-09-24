# Private image registry for the meeting transcriber

**State:** open
**Scope:** undecided
**Destination:** deployment
**Revisit when:** the user picks a registry host for the meeting transcriber image.

The meeting transcriber (`src/meeting`, the `Dockerfile` and `docker/`) turns
one meeting recording into a named transcript. It is handed to colleagues as a
pilot. It has no feature folder yet, so Scope stays undecided until its identity
as a feature is agreed. This record moved here from YIAN on 2026-09-24,
together with the code.

Today it ships as a file. `docker/build.ps1 -Export <shared folder>` writes
`meeting-transcriber.tar` together with the `.bat` scripts, and colleagues load
it with `Installa.bat` (`docker load`). This was confirmed on 2026-09-24 as the
way to finish the pilot.

A private registry would make updates cheap: the Dockerfile orders its layers
dependencies → models → code, so a pull would download only the code layer of a
few KB instead of the whole image, about 7 GB compressed. The idea was discussed and explicitly
postponed ("non facciamolo ora"). It can wait because it needs decisions that
belong to the user or the company:

- the host: GHCR, a private Docker Hub repository, or Azure Container Registry;
- read-only credentials for colleagues;
- plan limits for a private image of about 7 GB compressed.

## Planned change once a host is chosen

- `build.ps1 -Push`;
- `Installa.bat` runs `docker login` and `pull`;
- `Trascrivi.bat` does a quiet `pull` at start and falls back to the local image
  when offline.
