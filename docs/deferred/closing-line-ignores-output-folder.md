# Closing line ignores the output folder

**State:** closed
**Scope:** feature:agent-cli
**Destination:** implementation
**Revisit when:** the progress lines of `transcribe` are next changed, or sooner
if a person looks for a transcript next to the recording after giving an output
folder.

When `transcribe` gets `--out-dir`, it writes the transcript's text and JSON
files into that folder, as
[Transcribing](../features/agent-cli/frontend/agent-command-surface.md#transcribing)
states, but its closing progress line still says "Accanto alla registrazione
trovi '…' e '…'." It names only the files, so a person reading it looks in the
recording's folder and does not find them. The result summary on standard
output is right: its `transcript_txt` and `transcript_json` hold the real
paths.

The line is written in `_transcribe` in `src/transcriber/runner.py` whatever
`out_dir` is; `output_paths` in the same file already knows the folder. Seen on
2026-09-25, when a recording was transcribed a second time into a test folder.

A possible outcome: keep the line as it is when no output folder is given, and
otherwise name the folder, for example "Nella cartella <cartella> trovi '…' e
'…'.", with a test in `tests/test_transcriber.py` or `tests/test_cli.py`.

## Resolution

Fixed on 2026-09-25. With an output folder, the closing line now names it as
the person sees it on their PC, "Nella cartella <cartella> trovi '…' e '…'.";
without one it is unchanged. The folder follows
[Transcribing](../features/agent-cli/frontend/agent-command-surface.md#transcribing),
and `test_run_names_the_output_folder_when_one_is_given` in
`tests/test_transcriber.py` covers the line.
