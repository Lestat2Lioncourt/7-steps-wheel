"""
Roue CSI - Point d'entree de l'application Flask.
Lance le serveur local et ouvre le navigateur automatiquement.
"""

import webbrowser
import threading
from flask import Flask
from app.database.db import init_db

HOST = "127.0.0.1"
PORT = 5000


def create_app() -> Flask:
    """Factory Flask : cree et configure l'application."""
    application = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    # Cle secrete pour les sessions Flask
    application.secret_key = "roue-csi-standalone-key"

    # Initialisation de la base au demarrage
    init_db()

    # Enregistrement du blueprint principal
    from app.routes.main import main_bp
    application.register_blueprint(main_bp)

    return application


app = create_app()


def open_browser():
    """Ouvre le navigateur apres un court delai (laisse le serveur demarrer)."""
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(host=HOST, port=PORT, debug=True)
