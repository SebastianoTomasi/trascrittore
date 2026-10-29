"""
The transcriber's commands. None of them asks a question: each takes everything from its arguments,
prints lines for people on standard error, and ends with one JSON result summary on standard output.

Trascrivi.bat asks the person and calls these same commands through docker/trascrittore.ps1.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from src.settings import SettingsError
from src.transcriber.summary import INVALID_ARGUMENTS, INVALID_SETTINGS, emit, failure, say


class _UsageError(Exception):
    def __init__(self, message: str, usage: str):
        super().__init__(message)
        self.usage = usage


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise _UsageError(message, self.format_usage())


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' non è un numero intero.") from None
    if number < 1:
        raise argparse.ArgumentTypeError(f"'{value}' deve essere almeno 1.")
    return number


def _parser() -> _Parser:
    parser = _Parser(
        prog="python -m src.transcriber",
        description=(
            "Trascrive registrazioni in italiano con i nomi di chi parla. Nessun comando fa domande: "
            "le righe per le persone vanno su stderr, e ogni comando finisce con un riepilogo JSON su stdout. "
            "Uscita: 0 riuscito, 2 argomenti non validi, 130 interrotto, 1 ogni altro errore."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMANDO", parser_class=_Parser)

    transcribe = commands.add_parser("transcribe", help="trascrive una registrazione")
    transcribe.add_argument("recording", help="file audio o video (wav, mp3, m4a, mp4, ...)")
    transcribe.add_argument("--speakers", type=_positive_int, default=None, help="numero esatto di persone che parlano")
    transcribe.add_argument(
        "--out-dir",
        default=None,
        help="dove creare la cartella della trascrizione (default: accanto alla registrazione, che poi ci sposta)",
    )

    name = commands.add_parser(
        "name",
        help="dà un nome alle voci e aggiunge le loro clip alla libreria delle voci",
        description=(
            "Riscrive i due file della trascrizione con i nomi dati, senza trascrivere di nuovo, e aggiunge "
            "le clip di ogni voce nominata alla libreria. Solo una persona dà i nomi: un agente usa solo nomi "
            "che la persona ha confermato o scritto, dopo che ha ascoltato le clip di 'listen'. Una voce "
            "riconosciuta si conferma o si corregge solo quando la persona lo chiede."
        ),
    )
    name.add_argument("transcript", help="il file '<nome>-trascrizione.json'")
    name.add_argument("names", nargs="*", metavar="ETICHETTA=NOME", help='per esempio "Persona 2=Luca Bianchi"')
    name.add_argument("--recording", default=None, help="la registrazione, se non è più dove dice la trascrizione")
    name.add_argument(
        "--confirm", action="append", default=[], metavar="ETICHETTA",
        help="una voce riconosciuta che la persona conferma: aggiunge altre sue clip; ripetibile",
    )
    name.add_argument(
        "--correct", action="store_true",
        help="permette di sostituire il nome di una voce riconosciuta, quando la persona lo corregge",
    )
    name.add_argument(
        "--new-person", action="append", default=[], metavar="NOME",
        help="un nome che la persona conferma come persona nuova, anche se somiglia a uno della libreria; ripetibile",
    )

    listen = commands.add_parser(
        "listen", help="prepara una clip di una voce da ascoltare prima di nominarla; una voce alla volta"
    )
    listen.add_argument("transcript", help="il file '<nome>-trascrizione.json'")
    listen.add_argument("label", metavar="ETICHETTA", help='per esempio "Persona 2"')
    listen.add_argument("--recording", default=None, help="la registrazione, se non è più dove dice la trascrizione")
    listen.add_argument("--out-dir", default=None, help="cartella delle clip da ascoltare")
    listen.add_argument("--clip", type=_positive_int, default=1, help="quale clip: 1 la migliore, 2 la seconda, ...")

    remove = commands.add_parser(
        "remove-clips",
        help="toglie dalla libreria clip aggiunte da 'name', dopo che la persona ha confermato la proposta",
    )
    remove.add_argument("person", help="il nome della cartella della persona in 'voci'")
    remove.add_argument("clips", nargs="+", metavar="CLIP", help="i file proposti da 'name' in 'over_cap'")
    return parser


def _transcribe(args: argparse.Namespace) -> dict[str, Any]:
    from src.transcriber import runner

    return runner.run(args.recording, speakers=args.speakers, out_dir=args.out_dir)


def _name(args: argparse.Namespace) -> dict[str, Any]:
    from src.transcriber import naming

    return naming.name_speakers(
        args.transcript,
        args.names,
        recording=args.recording,
        confirm=args.confirm,
        correct=args.correct,
        new_people=args.new_person,
    )


def _listen(args: argparse.Namespace) -> dict[str, Any]:
    from src.transcriber import naming

    return naming.prepare_listening(
        args.transcript, args.label, recording=args.recording, out_dir=args.out_dir, clip=args.clip
    )


def _remove_clips(args: argparse.Namespace) -> dict[str, Any]:
    from src.transcriber import library

    return library.remove_clips_report(args.person, args.clips)


_COMMANDS = {
    "transcribe": _transcribe,
    "name": _name,
    "listen": _listen,
    "remove-clips": _remove_clips,
}


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except _UsageError as exc:
        say(f"Errore: {exc}")
        say(exc.usage.rstrip())
        command = next((arg for arg in (sys.argv[1:] if argv is None else argv) if arg in _COMMANDS), None)
        return emit(failure(command, INVALID_ARGUMENTS, f"Argomenti non validi: {exc}"))

    from dotenv import load_dotenv

    from src.utils.logging_setup import init_logging

    init_logging()
    load_dotenv()
    try:
        import src.asr.utils.config  # noqa: F401 - reads the settings once, before the command runs
    except SettingsError as exc:
        say(f"Errore: {exc}")
        return emit(failure(args.command, INVALID_SETTINGS, str(exc)))
    return emit(_COMMANDS[args.command](args))
