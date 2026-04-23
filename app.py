from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import os

from model import load_data
from ui import BotlaneUI


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    data_path = Path(os.environ.get("BOTLANE_DATA_XLSX", repo_root / "data.xlsx"))

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
        champion_id_json_path=repo_root / "champion_id_to_name.json",
    )

    root = tk.Tk()
    BotlaneUI(root, model=model, icons_dir=repo_root / "champion-icons")
    root.mainloop()


if __name__ == "__main__":
    main()
