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
        self.results_best_first = True
        self.enemy_results_best_first = False

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

        pairs_region = ttk.Frame(left)
        pairs_region.pack(fill=tk.BOTH, expand=True)

        self.result_box = ttk.LabelFrame(pairs_region, text="Paires alliées")
        self.result_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self._build_allied_pairs_panel()

        self.enemy_result_box = ttk.LabelFrame(pairs_region, text="Paires ennemies")
        self.enemy_result_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        self._build_enemy_pairs_panel()

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

    def _build_allied_pairs_panel(self) -> None:
        result_toolbar = ttk.Frame(self.result_box)
        result_toolbar.pack(fill=tk.X, padx=8, pady=(8, 0))
        self.best_button = tk.Button(result_toolbar, text="Meilleures", command=lambda: self.set_results_sort(True))
        self.best_button.pack(side=tk.LEFT)
        self.worst_button = tk.Button(result_toolbar, text="Pires", command=lambda: self.set_results_sort(False))
        self.worst_button.pack(side=tk.LEFT, padx=(6, 0))

        self.results_area = ttk.Frame(self.result_box)
        self.results_area.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        results_header = ttk.Frame(self.results_area)
        results_header.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(results_header, text="Score", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(156, 0))
        results_body = ttk.Frame(self.results_area)
        results_body.pack(fill=tk.BOTH, expand=True)
        self.results_canvas = tk.Canvas(results_body, borderwidth=0, highlightthickness=0)
        self.results_scrollbar = ttk.Scrollbar(results_body, orient=tk.VERTICAL, command=self.results_canvas.yview)
        self.results_canvas.configure(yscrollcommand=self.results_scrollbar.set)
        self.results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.root.bind_all("<MouseWheel>", self._on_results_mousewheel)
        self.root.bind_all("<Button-4>", self._on_results_mousewheel)
        self.root.bind_all("<Button-5>", self._on_results_mousewheel)

        self.results_container = ttk.Frame(self.results_canvas)
        self.results_canvas_window = self.results_canvas.create_window((0, 0), window=self.results_container, anchor="nw")
        self.results_container.bind("<Configure>", self._on_results_configure)
        self.results_canvas.bind("<Configure>", self._on_results_canvas_configure)

    def _build_enemy_pairs_panel(self) -> None:
        result_toolbar = ttk.Frame(self.enemy_result_box)
        result_toolbar.pack(fill=tk.X, padx=8, pady=(8, 0))
        self.enemy_best_button = tk.Button(result_toolbar, text="Meilleures", command=lambda: self.set_enemy_results_sort(True))
        self.enemy_best_button.pack(side=tk.LEFT)
        self.enemy_worst_button = tk.Button(result_toolbar, text="Pires", command=lambda: self.set_enemy_results_sort(False))
        self.enemy_worst_button.pack(side=tk.LEFT, padx=(6, 0))

        self.enemy_results_area = ttk.Frame(self.enemy_result_box)
        self.enemy_results_area.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        results_header = ttk.Frame(self.enemy_results_area)
        results_header.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(results_header, text="Score", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(156, 0))
        results_body = ttk.Frame(self.enemy_results_area)
        results_body.pack(fill=tk.BOTH, expand=True)
        self.enemy_results_canvas = tk.Canvas(results_body, borderwidth=0, highlightthickness=0)
        self.enemy_results_scrollbar = ttk.Scrollbar(results_body, orient=tk.VERTICAL, command=self.enemy_results_canvas.yview)
        self.enemy_results_canvas.configure(yscrollcommand=self.enemy_results_scrollbar.set)
        self.enemy_results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.enemy_results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.enemy_results_container = ttk.Frame(self.enemy_results_canvas)
        self.enemy_results_canvas_window = self.enemy_results_canvas.create_window((0, 0), window=self.enemy_results_container, anchor="nw")
        self.enemy_results_container.bind("<Configure>", self._on_enemy_results_configure)
        self.enemy_results_canvas.bind("<Configure>", self._on_enemy_results_canvas_configure)

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

    def set_results_sort(self, best_first: bool) -> None:
        self.results_best_first = best_first
        self._refresh_sort_buttons()
        self._refresh_allied_results()

    def set_enemy_results_sort(self, best_first: bool) -> None:
        self.enemy_results_best_first = best_first
        self._refresh_sort_buttons()
        self._refresh_enemy_results()

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
        self._refresh_sort_buttons()
        self._refresh_allied_results()
        self._refresh_enemy_results()

    def _refresh_allied_results(self) -> None:
        for child in self.results_container.winfo_children():
            child.destroy()

        all_pair_count = len(self.model.adc_ally) * len(self.model.sup_ally)
        pairs = recommend_pairs(self.model, self.state, top_k=all_pair_count)
        if not self.results_best_first:
            pairs.reverse()

        self._render_pair_rows(self.results_container, pairs)

    def _refresh_enemy_results(self) -> None:
        for child in self.enemy_results_container.winfo_children():
            child.destroy()

        pairs = self._recommend_enemy_pairs()
        pairs.sort(key=lambda item: item[2], reverse=self.enemy_results_best_first)
        self._render_pair_rows(self.enemy_results_container, pairs)

    def _recommend_enemy_pairs(self) -> list[tuple[str, str, float]]:
        if not self.state.adc_ally and not self.state.sup_ally:
            return []

        banned = self.state.bans or set()
        taken_allies = {c for c in [self.state.adc_ally, self.state.sup_ally] if c}
        taken_enemies = {c for c in [self.state.adc_enemy, self.state.sup_enemy] if c}

        adc_candidates = [self.state.adc_enemy] if self.state.adc_enemy else self.model.adc_meta[:20]
        sup_candidates = [self.state.sup_enemy] if self.state.sup_enemy else self.model.sup_meta[:20]

        results: list[tuple[str, str, float]] = []
        for enemy_adc in adc_candidates:
            if enemy_adc in banned or enemy_adc in taken_allies:
                continue
            for enemy_sup in sup_candidates:
                if enemy_sup in banned or enemy_sup in taken_allies:
                    continue
                if enemy_adc == enemy_sup:
                    continue
                if enemy_adc in taken_enemies - {self.state.adc_enemy}:
                    continue
                if enemy_sup in taken_enemies - {self.state.sup_enemy}:
                    continue

                score = self._score_allies_into_enemy_pair(enemy_adc, enemy_sup)
                if score is not None:
                    results.append((enemy_adc, enemy_sup, score))
        return results

    def _score_allies_into_enemy_pair(self, enemy_adc: str, enemy_sup: str) -> Optional[float]:
        selected_allies = [c for c in [self.state.adc_ally, self.state.sup_ally] if c]
        if not selected_allies:
            return None

        enemies = [enemy_adc, enemy_sup]
        counter_score = sum(
            self.model.counter.get(ally, {}).get(enemy, 0.0)
            for ally in selected_allies
            for enemy in enemies
        )
        counter_score /= len(selected_allies) * len(enemies)

        if self.state.adc_ally and self.state.sup_ally:
            counter_score += self.model.synergy.get(self.state.adc_ally, {}).get(self.state.sup_ally, 0.0)

        return counter_score

    def _render_pair_rows(self, container: ttk.Frame, pairs: list[tuple[str, str, float]]) -> None:
        max_positive = max((score for _, _, score in pairs), default=0.0)
        max_negative = abs(min((score for _, _, score in pairs), default=0.0))

        for adc, sup, score in pairs:
            row = ttk.Frame(container)
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
            ttk.Label(
                row,
                text=f"{score:.2f}",
                foreground=self._score_color(score, max_positive, max_negative),
                font=("Segoe UI", 11),
            ).pack(side=tk.LEFT)

    def _score_color(self, score: float, max_positive: float, max_negative: float) -> str:
        if score > 0 and max_positive > 0:
            intensity = round(180 * score / max_positive)
            return f"#00{intensity:02x}00"
        if score < 0 and max_negative > 0:
            intensity = round(220 * abs(score) / max_negative)
            return f"#{intensity:02x}0000"
        return "#000000"

    def _refresh_everything(self) -> None:
        self._refresh_slots()
        self._refresh_bans()
        self._refresh_selector()
        self._refresh_results()

    def _refresh_sort_buttons(self) -> None:
        active_options = {"relief": tk.SUNKEN, "bg": "#d9eaf7"}
        inactive_options = {"relief": tk.RAISED, "bg": self.root.cget("bg")}
        self.best_button.config(**(active_options if self.results_best_first else inactive_options))
        self.worst_button.config(**(inactive_options if self.results_best_first else active_options))
        self.enemy_best_button.config(**(active_options if self.enemy_results_best_first else inactive_options))
        self.enemy_worst_button.config(**(inactive_options if self.enemy_results_best_first else active_options))

    def _on_selector_configure(self, _event: tk.Event) -> None:
        self.selector_canvas.configure(scrollregion=self.selector_canvas.bbox("all"))

    def _on_selector_canvas_configure(self, event: tk.Event) -> None:
        self.selector_canvas.itemconfigure(self.selector_canvas_window, width=event.width)

    def _on_results_configure(self, _event: tk.Event) -> None:
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))

    def _on_results_canvas_configure(self, event: tk.Event) -> None:
        self.results_canvas.itemconfigure(self.results_canvas_window, width=event.width)

    def _on_enemy_results_configure(self, _event: tk.Event) -> None:
        self.enemy_results_canvas.configure(scrollregion=self.enemy_results_canvas.bbox("all"))

    def _on_enemy_results_canvas_configure(self, event: tk.Event) -> None:
        self.enemy_results_canvas.itemconfigure(self.enemy_results_canvas_window, width=event.width)

    def _on_results_mousewheel(self, event: tk.Event) -> Optional[str]:
        target_canvas = self._results_canvas_under_pointer()
        if target_canvas is None:
            return None

        if getattr(event, "num", None) == 4:
            direction = -1
        elif getattr(event, "num", None) == 5:
            direction = 1
        else:
            direction = -1 if event.delta > 0 else 1
        target_canvas.yview_scroll(direction, "units")
        return "break"

    def _results_canvas_under_pointer(self) -> Optional[tk.Canvas]:
        pointer_x = self.root.winfo_pointerx()
        pointer_y = self.root.winfo_pointery()
        for box, canvas in [(self.result_box, self.results_canvas), (self.enemy_result_box, self.enemy_results_canvas)]:
            area_x = box.winfo_rootx()
            area_y = box.winfo_rooty()
            area_width = box.winfo_width()
            area_height = box.winfo_height()
            if area_x <= pointer_x <= area_x + area_width and area_y <= pointer_y <= area_y + area_height:
                return canvas
        return None
