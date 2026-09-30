# Private image registry for the transcriber

**State:** open
**Scope:** project
**Destination:** deployment
**Revisit when:** the maintainer picks a registry host for the transcriber image.

The transcriber (`src/transcriber`, the `Dockerfile` and `docker/`) turns
one recording into a transcript with the speakers' names. It is a personal tool handed to people
close to the maintainer. This record moved here from YIAN on 2026-09-24,
together with the code; the transcriber is now the whole project, so
the record has project scope.

Today it ships as local files. `docker/build.ps1 -Variant both -Export <export folder>`
writes `trascrittore-cu126.tar` and `trascrittore-cu128.tar` with the installer
and launcher; a person downloads both or just the TAR for their GPU.
`Installa.bat` selects and checks one image before making it active.
The file-based delivery method was chosen on 2026-09-24 for the pilot.

A private registry would make updates cheap: the Dockerfile orders its layers
dependencies → models → code, so a pull would download only the code layer of a
few KB instead of a whole image, about 7 GB compressed. The idea was discussed and explicitly
postponed ("non facciamolo ora"). It can wait because it needs decisions that
belong to the maintainer:

- the host: GHCR, a private Docker Hub repository, or Azure Container Registry;
- read-only credentials for the people who use it;
- plan limits for a private image of about 7 GB compressed.

## Planned change once a host is chosen

- `build.ps1 -Push`;
- `Installa.bat` runs `docker login` and `pull`;
- `Trascrivi.bat` does a quiet `pull` at start and falls back to the local image
  when offline;
- the agent skill follows the image on the same path, as
  [skill delivery](../features/agent-cli/deployment/skill-delivery.md#later)
  requires.
