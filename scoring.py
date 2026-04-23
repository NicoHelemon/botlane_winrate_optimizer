from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from model import DataModel


@dataclass
class DraftState:
    adc_ally: Optional[str] = None
    sup_ally: Optional[str] = None
    adc_enemy: Optional[str] = None
    sup_enemy: Optional[str] = None
    bans: Optional[set[str]] = None

    def __post_init__(self) -> None:
        if self.bans is None:
            self.bans = set()


def _known_enemies(state: DraftState) -> List[str]:
    return [c for c in [state.adc_enemy, state.sup_enemy] if c]


def _counter_mean(model: DataModel, adc: str, sup: str, enemies: Sequence[str]) -> float:
    if not enemies:
        return 0.0
    total = 0.0
    for ally in (adc, sup):
        for enemy in enemies:
            total += model.counter.get(ally, {}).get(enemy, 0.0)
    return total / (2 * len(enemies))


def score_pair(model: DataModel, adc: str, sup: str, state: DraftState, synergy_weight: float = 2.0) -> float:
    enemies = _known_enemies(state)
    synergy = model.synergy.get(adc, {}).get(sup, 0.0)
    return _counter_mean(model, adc, sup, enemies) + synergy_weight * synergy


def recommend_pairs(
    model: DataModel,
    state: DraftState,
    top_k: int = 6,
    synergy_weight: float = 2.0,
) -> List[Tuple[str, str, float]]:
    banned = state.bans or set()
    already_taken = {c for c in [state.adc_ally, state.sup_ally, state.adc_enemy, state.sup_enemy] if c}

    adc_candidates = [state.adc_ally] if state.adc_ally else model.adc_ally
    sup_candidates = [state.sup_ally] if state.sup_ally else model.sup_ally

    results: List[Tuple[str, str, float]] = []
    for adc in adc_candidates:
        if adc in banned:
            continue
        for sup in sup_candidates:
            if sup in banned:
                continue
            if adc == sup:
                continue
            if adc in already_taken - {state.adc_ally}:
                continue
            if sup in already_taken - {state.sup_ally}:
                continue
            score = score_pair(model, adc, sup, state, synergy_weight=synergy_weight)
            results.append((adc, sup, score))

    results.sort(key=lambda item: item[2], reverse=True)
    return results[:top_k]


def available_for_slot(model: DataModel, state: DraftState, slot: str) -> List[str]:
    taken = {c for c in [state.adc_ally, state.sup_ally, state.adc_enemy, state.sup_enemy] if c}
    bans = state.bans or set()

    slot_to_pool = {
        "adc_ally": model.adc_ally,
        "sup_ally": model.sup_ally,
        "adc_enemy": model.adc_meta,
        "sup_enemy": model.sup_meta,
        "ban": sorted(set(model.adc_ally + model.sup_ally + model.adc_meta + model.sup_meta)),
    }
    if slot not in slot_to_pool:
        raise ValueError(f"slot inconnu: {slot}")

    current = getattr(state, slot, None) if slot != "ban" else None
    blocked = (taken - ({current} if current else set())) | bans
    return [champ for champ in slot_to_pool[slot] if champ not in blocked]
