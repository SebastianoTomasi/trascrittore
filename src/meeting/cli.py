from __future__ import annotations

import argparse


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' non è un numero intero.") from None
    if number < 1:
        raise argparse.ArgumentTypeError("il numero di persone deve essere almeno 1.")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.meeting",
        description="Trascrive l'audio di una riunione con i nomi di chi parla.",
    )
    parser.add_argument("audio", help="file audio o video della riunione (wav, mp3, m4a, mp4, ...)")
    parser.add_argument("--speakers", type=_positive_int, default=None, help="numero esatto di persone che parlano")
    parser.add_argument(
        "--ask-names",
        action="store_true",
        help="alla fine chiede un nome per le voci non riconosciute",
    )
    parser.add_argument("--out-dir", default=None, help="cartella di output (default: quella dell'audio)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from dotenv import load_dotenv

    from src.utils.logging_setup import init_logging

    init_logging()
    load_dotenv()

    from src.meeting.runner import run

    return run(args.audio, speakers=args.speakers, ask_names=args.ask_names, out_dir=args.out_dir)
