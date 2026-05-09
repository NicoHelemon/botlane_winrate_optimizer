from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import os
import sys

from model import load_data
from ui import BotlaneUI


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _bundled_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return _app_root()


def _resource_path(relative_path: str) -> Path:
    app_resource = _app_root() / relative_path
    if app_resource.exists():
        return app_resource
    return _bundled_root() / relative_path


def main() -> None:
    default_data_path = _resource_path("data.xlsx")
    data_path = Path(os.environ.get("BOTLANE_DATA_XLSX", default_data_path))

    if not data_path.exists():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Fichier manquant",
            "Impossible de démarrer: fichier data.xlsx introuvable.\n"
            "Place ton fichier Excel puis relance, ou définis BOTLANE_DATA_XLSX.",
        )
        return

    model = load_data(
        excel_path=data_path,
        champion_id_json_path=_resource_path("champion_id_to_name.json"),
    )

    root = tk.Tk()
    BotlaneUI(root, model=model, icons_dir=_resource_path("champion-icons"))
    root.mainloop()


if __name__ == "__main__":
    main()
