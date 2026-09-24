"""
The transcriber's commands. None of them asks a question: each takes everything from its arguments,
prints lines for people on standard error, and ends with one JSON result summary on standard output.

Trascrivi.bat asks the person and calls these same commands through docker/trascrittore.ps1.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from src.meeting.summary import INVALID_ARGUMENTS, emit, failure, say


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
        raise argparse.ArgumentTypeError("il numero di persone deve essere almeno 1.")
    return number


def _parser() -> _Parser:
    parser = _Parser(
        prog="python -m src.meeting",
        description=(
            "Trascrive registrazioni in italiano con i nomi di chi parla. Nessun comando fa domande: "
            "le righe per le persone vanno su stderr, e ogni comando finisce con un riepilogo JSON su stdout. "
            "Uscita: 0 riuscito, 2 argomenti non validi, 130 interrotto, 1 ogni altro errore."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMANDO", parser_class=_Parser)

    transcribe = commands.add_parser("transcribe", help="trascrive una registrazione")
    transcribe.add_argument("audio", help="file audio o video (wav, mp3, m4a, mp4, ...)")
    transcribe.add_argument("--speakers", type=_positive_int, default=None, help="numero esatto di persone che parlano")
    transcribe.add_argument("--out-dir", default=None, help="cartella dei file di uscita (default: quella della registrazione)")

    name = commands.add_parser(
        "name",
        help="dà un nome alle voci 'Persona N' e aggiunge le loro clip alla libreria delle voci",
        description=(
            "Riscrive i due file della trascrizione con i nomi dati, senza trascrivere di nuovo, e aggiunge "
            "le clip di ogni voce nominata alla libreria. Solo una persona dà i nomi: un agente usa solo nomi "
            "che la persona ha confermato o scritto, dopo che ha ascoltato le clip preparate da 'listen'."
        ),
    )
    name.add_argument("transcript", help="il file '<nome> - trascrizione.json'")
    name.add_argument("names", nargs="+", metavar="ETICHETTA=NOME", help='per esempio "Persona 2=Luca Bianchi"')
    name.add_argument("--recording", default=None, help="la registrazione, se non è più dove dice la trascrizione")

    listen = commands.add_parser("listen", help="prepara le 1-2 clip migliori di ogni voce da ascoltare prima di nominarla")
    listen.add_argument("transcript", help="il file '<nome> - trascrizione.json'")
    listen.add_argument("labels", nargs="+", metavar="ETICHETTA", help='per esempio "Persona 2"')
    listen.add_argument("--recording", default=None, help="la registrazione, se non è più dove dice la trascrizione")
    listen.add_argument("--out-dir", default=None, help="cartella delle clip da ascoltare")

    check = commands.add_parser(
        "check",
        help="verifica quanto bene la libreria delle voci riconosce le persone, e suggerisce una soglia",
        description=(
            "Usa le voci a cui una persona ha dato il nome nelle trascrizioni del PC: senza --pair né --missing, "
            "le trascrizioni da cui sono state aggiunte clip alla libreria. Non cambia mai meeting.ini."
        ),
    )
    check.add_argument(
        "--pair",
        nargs=2,
        action="append",
        metavar=("TRASCRIZIONE", "REGISTRAZIONE"),
        help="una trascrizione .json e la sua registrazione; ripetibile",
    )
    check.add_argument("--missing", action="append", default=[], help="una trascrizione non trovata, da elencare come saltata")

    trial = commands.add_parser(
        "trial",
        help="riporta il periodo di prova della selezione delle clip",
        description=(
            "Confronta i voti della selezione con le clip che la persona ha cancellato. Dopo 10 voci nominate "
            "senza disaccordi, e solo con --reviewed, la selezione scarta da sola le clip peggiori."
        ),
    )
    trial.add_argument(
        "--reviewed",
        action="store_true",
        help="la persona conferma di aver ascoltato tutte le clip aggiunte e cancellato quelle brutte",
    )
    return parser


def _transcribe(args: argparse.Namespace) -> dict[str, Any]:
    from src.meeting import runner

    return runner.run(args.audio, speakers=args.speakers, out_dir=args.out_dir)


def _name(args: argparse.Namespace) -> dict[str, Any]:
    from src.meeting import naming

    return naming.name_speakers(args.transcript, args.names, recording=args.recording)


def _listen(args: argparse.Namespace) -> dict[str, Any]:
    from src.meeting import naming

    return naming.prepare_listening(args.transcript, args.labels, recording=args.recording, out_dir=args.out_dir)


def _check(args: argparse.Namespace) -> dict[str, Any]:
    from src.meeting import recognition_check

    # Only a run with nothing given looks for transcripts itself: the launcher always says what it found.
    given = bool(args.pair or args.missing)
    pairs = [tuple(pair) for pair in args.pair or []] if given else None
    return recognition_check.run_check(pairs, missing=args.missing)


def _trial(args: argparse.Namespace) -> dict[str, Any]:
    from src.asr.utils.config import get_library_settings
    from src.meeting import library
    from src.meeting.summary import guarded

    return guarded(
        "trial",
        lambda: library.trial_report(get_library_settings(), reviewed=args.reviewed),
        failed="Il resoconto del periodo di prova non è riuscito",
    )


_COMMANDS = {"transcribe": _transcribe, "name": _name, "listen": _listen, "check": _check, "trial": _trial}


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
    return emit(_COMMANDS[args.command](args))
