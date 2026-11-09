"""Avvio: python -m consigliere [--cartella DIR] [--senza-browser]."""
import argparse
import sys
import webbrowser
from pathlib import Path

if sys.version_info < (3, 11):
    sys.exit("Serve Python 3.11 o successivo. Segui la GUIDA.md per installarlo.")

from consigliere.server import crea_server  # noqa: E402


def main():
    p = argparse.ArgumentParser(prog="consigliere")
    p.add_argument("--cartella", type=Path, default=Path.home() / "ConsiglioFormazione")
    p.add_argument("--porta", type=int, default=8765)
    p.add_argument("--senza-browser", action="store_true")
    a = p.parse_args()
    a.cartella.mkdir(parents=True, exist_ok=True)
    try:
        srv = crea_server(a.cartella, a.porta)
    except OSError:
        srv = crea_server(a.cartella, 0)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"Consigliere di formazione aperto su {url}", flush=True)
    print(f"Dati in {a.cartella}", flush=True)
    print("Lascia aperta questa finestra; per chiudere il programma premi Ctrl+C o chiudila.", flush=True)
    if not a.senza_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
