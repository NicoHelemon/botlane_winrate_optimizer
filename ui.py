from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

from model import DataModel
from scoring import DraftState, available_for_slot, recommend_pairs


SLOT_LABELS = {
    "adc_ally": "ADC allié",
    "sup_ally": "Support allié",
    "adc_enemy": "ADC ennemi",
    "sup_enemy": "Support ennemi",
}


class BotlaneUI:
    def __init__(self, root: tk.Tk, model: DataModel, icons_dir: Path) -> None:
        self.root = root
        self.model = model
        self.icons_dir = icons_dir
        self.state = DraftState()
        self.active_target: Optional[str] = None
        self.icon_cache: Dict[str, tk.PhotoImage] = {}

        self.root.title("Botlane Winrate Optimizer")
        self.root.geometry("1200x760")

        self._build()
        self._refresh_everything()

    def _build(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill=tk.X)

        bans_frame = ttk.LabelFrame(top, text="Bans")
        bans_frame.pack(fill=tk.X)
        self.bans_container = ttk.Frame(bans_frame)
        self.bans_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=8)
        ttk.Button(bans_frame, text="+ Add ban", command=lambda: self.open_selector("ban")).pack(side=tk.RIGHT, padx=8, pady=8)

        main = ttk.Frame(self.root, padding=(12, 6, 12, 12))
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right = ttk.LabelFrame(main, text="Sélection champion")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(12, 0))

        self.pick_frame = ttk.Frame(left)
        self.pick_frame.pack(fill=tk.X, pady=(0, 12))

        self.slot_widgets: Dict[str, ttk.Frame] = {}
        for idx, slot in enumerate(["adc_ally", "sup_ally", "adc_enemy", "sup_enemy"]):
            widget = self._build_slot(self.pick_frame, slot)
            widget.grid(row=0, column=idx, padx=8)
            self.slot_widgets[slot] = widget

        result_box = ttk.LabelFrame(left, text="Top 6 paires")
        result_box.pack(fill=tk.BOTH, expand=True)
        self.results_container = ttk.Frame(result_box)
        self.results_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        action_frame = ttk.Frame(left)
        action_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(action_frame, text="Clear all", command=self.clear_all).pack(side=tk.LEFT)

        search_frame = ttk.Frame(right)
        search_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(search_frame, text="Recherche:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_selector())
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        self.selector_canvas = tk.Canvas(right, borderwidth=0, highlightthickness=0)
        self.selector_scrollbar = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.selector_canvas.yview)
        self.selector_canvas.configure(yscrollcommand=self.selector_scrollbar.set)
        self.selector_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=(0, 8))
        self.selector_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))

        self.selector_grid = ttk.Frame(self.selector_canvas)
        self.selector_canvas_window = self.selector_canvas.create_window((0, 0), window=self.selector_grid, anchor="nw")
        self.selector_grid.bind("<Configure>", self._on_selector_configure)
        self.selector_canvas.bind("<Configure>", self._on_selector_canvas_configure)

    def _build_slot(self, parent: ttk.Frame, slot: str) -> ttk.Frame:
        card = ttk.Frame(parent, relief=tk.GROOVE, padding=8)
        ttk.Label(card, text=SLOT_LABELS[slot], font=("Segoe UI", 10, "bold")).pack()
        icon = ttk.Label(card)
        icon.pack(pady=(6, 2))
        name = ttk.Label(card, text="(vide)")
        name.pack()
        action_row = ttk.Frame(card)
        action_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(action_row, text="Choisir", command=lambda s=slot: self.open_selector(s)).pack(side=tk.LEFT)
        ttk.Button(action_row, text="×", width=3, command=lambda s=slot: self.clear_slot(s)).pack(side=tk.RIGHT)

        card.icon_label = icon  # type: ignore[attr-defined]
        card.name_label = name  # type: ignore[attr-defined]
        return card

    def _get_icon(self, champion: str) -> Optional[tk.PhotoImage]:
        if champion in self.icon_cache:
            return self.icon_cache[champion]
        champ_id = self.model.name_to_id.get(champion)
        if not champ_id:
            return None
        path = self.icons_dir / f"{champ_id}.png"
        if not path.exists():
            return None
        img = tk.PhotoImage(file=str(path))
        img = img.subsample(2, 2)
        self.icon_cache[champion] = img
        return img

    def open_selector(self, slot: str) -> None:
        self.active_target = slot
        self._refresh_selector()

    def clear_slot(self, slot: str) -> None:
        setattr(self.state, slot, None)
        self._refresh_everything()

    def clear_ban(self, champion: str) -> None:
        self.state.bans.discard(champion)
        self._refresh_everything()

    def clear_all(self) -> None:
        self.state = DraftState()
        self.active_target = None
        self.search_var.set("")
        self._refresh_everything()

    def _select_champion(self, champion: str) -> None:
        if not self.active_target:
            return
        if self.active_target == "ban":
            self.state.bans.add(champion)
        else:
            setattr(self.state, self.active_target, champion)
        self._refresh_everything()

    def _refresh_selector(self) -> None:
        for child in self.selector_grid.winfo_children():
            child.destroy()
        if not self.active_target:
            return
        champs = available_for_slot(self.model, self.state, self.active_target)
        query = self.search_var.get().strip().lower()
        if query:
            champs = [c for c in champs if query in c.lower()]

        for idx, champ in enumerate(champs):
            row, col = divmod(idx, 3)
            item = ttk.Frame(self.selector_grid, relief=tk.GROOVE, padding=4)
            item.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            icon = self._get_icon(champ)
            btn = ttk.Button(item, text=champ, command=lambda c=champ: self._select_champion(c), width=14)
            if icon:
                btn.config(image=icon, compound=tk.TOP)
                btn.image = icon
            btn.pack()

    def _refresh_slots(self) -> None:
        for slot, card in self.slot_widgets.items():
            champion = getattr(self.state, slot)
            card.name_label.config(text=champion or "(vide)")  # type: ignore[attr-defined]
            icon = self._get_icon(champion) if champion else None
            card.icon_label.config(image=icon if icon else "")  # type: ignore[attr-defined]
            if icon:
                card.icon_label.image = icon  # type: ignore[attr-defined]

    def _refresh_bans(self) -> None:
        for child in self.bans_container.winfo_children():
            child.destroy()
        for champion in sorted(self.state.bans):
            item = ttk.Frame(self.bans_container, relief=tk.GROOVE, padding=4)
            item.pack(side=tk.LEFT, padx=4)
            icon = self._get_icon(champion)
            if icon:
                lbl = ttk.Label(item, image=icon)
                lbl.image = icon
                lbl.pack()
            ttk.Label(item, text=champion).pack()
            ttk.Button(item, text="×", width=3, command=lambda c=champion: self.clear_ban(c)).pack()

    def _refresh_results(self) -> None:
        for child in self.results_container.winfo_children():
            child.destroy()
        for adc, sup, score in recommend_pairs(self.model, self.state, top_k=10):
            row = ttk.Frame(self.results_container)
            row.pack(fill=tk.X, pady=2)
            adc_icon = self._get_icon(adc)
            sup_icon = self._get_icon(sup)
            if adc_icon:
                adc_lbl = ttk.Label(row, image=adc_icon)
                adc_lbl.image = adc_icon
                adc_lbl.pack(side=tk.LEFT)
            if sup_icon:
                sup_lbl = ttk.Label(row, image=sup_icon)
                sup_lbl.image = sup_icon
                sup_lbl.pack(side=tk.LEFT, padx=(4, 10))
            ttk.Label(row, text=f"score: {score:.3f}", font=("Segoe UI", 11)).pack(side=tk.LEFT)

    def _refresh_everything(self) -> None:
        self._refresh_slots()
        self._refresh_bans()
        self._refresh_selector()
        self._refresh_results()

    def _on_selector_configure(self, _event: tk.Event) -> None:
        self.selector_canvas.configure(scrollregion=self.selector_canvas.bbox("all"))

    def _on_selector_canvas_configure(self, event: tk.Event) -> None:
        self.selector_canvas.itemconfigure(self.selector_canvas_window, width=event.width)
