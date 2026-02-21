"""
Roue CSI - Lancement rapide.
Demarre le serveur Flask et ouvre le navigateur une seule fois.

Usage : double-clic sur start.py  OU  python start.py
"""

import os
import socket
import sys
import threading
import webbrowser

HOST = "127.0.0.1"
PORT = 5000


def port_in_use(host, port):
    """Verifie si le port est deja occupe."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def open_browser():
    """Ouvre le navigateur apres un court delai."""
    webbrowser.open(f"http://{HOST}:{PORT}")


def log(msg):
    """Print uniquement si stdout est disponible (pas en mode pythonw)."""
    try:
        print(msg)
    except Exception:
        pass


if __name__ == "__main__":
    # Le reloader Flask relance ce script en sous-processus avec WERKZEUG_RUN_MAIN=true.
    # Dans ce cas, on ne fait ni le check de port ni l'ouverture du navigateur.
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    if not is_reloader_child:
        if port_in_use(HOST, PORT):
            log(f"Le port {PORT} est deja occupe.")
            log(f"Le serveur tourne probablement deja -> ouverture du navigateur.")
            open_browser()
            sys.exit(0)

        # Ouvrir le navigateur une seule fois
        threading.Timer(1.2, open_browser).start()
        log(f"Serveur demarre sur http://{HOST}:{PORT}")
        log("Appuyez sur Ctrl+C pour arreter.\n")

    from app.main import app
    app.run(host=HOST, port=PORT, debug=True, use_reloader=True)
