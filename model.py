from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import zipfile
from typing import Dict, List, Tuple


@dataclass
class DataModel:
    adc_ally: List[str]
    sup_ally: List[str]
    adc_meta: List[str]
    sup_meta: List[str]
    counter: Dict[str, Dict[str, float]]
    synergy: Dict[str, Dict[str, float]]
    name_to_id: Dict[str, str]


NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
POOL_COLUMNS = ["Adc_ally", "Sup_ally", "Adc_meta", "Sup_meta"]


def _load_name_to_id(path: Path) -> Dict[str, str]:
    with path.open("r", encoding="utf-8") as f:
        id_to_name = json.load(f)
    return {name: champ_id for champ_id, name in id_to_name.items()}


def _col_to_idx(ref: str) -> int:
    col = ""
    for c in ref:
        if c.isalpha():
            col += c
        else:
            break
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _parse_sheet(xml_data: bytes) -> Dict[Tuple[int, int], str]:
    root = ET.fromstring(xml_data)
    values: Dict[Tuple[int, int], str] = {}
    for c in root.findall(".//x:sheetData/x:row/x:c", NS):
        ref = c.attrib.get("r", "A1")
        col_idx = _col_to_idx(ref)
        row_idx = int("".join(ch for ch in ref if ch.isdigit())) - 1

        text = ""
        inline = c.find("x:is/x:t", NS)
        if inline is not None and inline.text is not None:
            text = inline.text
        else:
            v = c.find("x:v", NS)
            if v is not None and v.text is not None:
                text = v.text
        values[(row_idx, col_idx)] = text
    return values


def _read_xlsx_sheets(path: Path) -> Dict[str, Dict[Tuple[int, int], str]]:
    with zipfile.ZipFile(path, "r") as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"].lstrip("/")
            for rel in rels
            if rel.tag.endswith("Relationship")
        }

        sheets: Dict[str, Dict[Tuple[int, int], str]] = {}
        for sheet in wb.findall(".//x:sheets/x:sheet", NS):
            name = sheet.attrib["name"]
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rel_map[rid]
            if not target.startswith("xl/"):
                target = f"xl/{target}"
            sheets[name] = _parse_sheet(zf.read(target))
    return sheets


def _read_table(sheet: Dict[Tuple[int, int], str]) -> Tuple[List[str], List[List[str]]]:
    max_row = max(r for r, _ in sheet.keys())
    max_col = max(c for _, c in sheet.keys())

    header = [sheet.get((0, c), "").strip() for c in range(max_col + 1)]
    rows: List[List[str]] = []
    for r in range(1, max_row + 1):
        rows.append([sheet.get((r, c), "").strip() for c in range(max_col + 1)])
    return header, rows


def load_data(excel_path: Path, champion_id_json_path: Path) -> DataModel:
    sheets = _read_xlsx_sheets(excel_path)
    required_sheets = {"Pools", "Counter", "Synergy"}
    missing = required_sheets.difference(sheets.keys())
    if missing:
        missing_txt = ", ".join(sorted(missing))
        raise ValueError(f"Le fichier data.xlsx doit contenir les onglets: Pools, Counter, Synergy (manquant: {missing_txt})")

    pools_header, pools_rows = _read_table(sheets["Pools"])
    counter_header, counter_rows = _read_table(sheets["Counter"])
    synergy_header, synergy_rows = _read_table(sheets["Synergy"])

    pools_col_index = {name: idx for idx, name in enumerate(pools_header) if name}
    for col in POOL_COLUMNS:
        if col not in pools_col_index:
            raise ValueError(f"Colonne manquante dans Pools: {col}")

    pools: Dict[str, List[str]] = {}
    for col in POOL_COLUMNS:
        i = pools_col_index[col]
        pools[col] = [row[i] for row in pools_rows if i < len(row) and row[i]]

    matrix_cols = pools["Adc_meta"] + pools["Sup_meta"]
    matrix_rows = pools["Adc_ally"] + pools["Sup_ally"]

    counter_col_map = {name: idx for idx, name in enumerate(counter_header)}
    if "Champion" not in counter_col_map:
        raise ValueError("Counter doit contenir une colonne Champion")
    champ_col = counter_col_map["Champion"]

    counter: Dict[str, Dict[str, float]] = {r: {} for r in matrix_rows}
    row_by_champion = {row[champ_col]: row for row in counter_rows if champ_col < len(row) and row[champ_col]}
    for ally in matrix_rows:
        row = row_by_champion.get(ally)
        if not row:
            continue
        for enemy in matrix_cols:
            idx = counter_col_map.get(enemy)
            if idx is None or idx >= len(row) or row[idx] == "":
                continue
            counter[ally][enemy] = float(row[idx])

    synergy_col_map = {name: idx for idx, name in enumerate(synergy_header)}
    if "Champion" not in synergy_col_map:
        raise ValueError("Synergy doit contenir une colonne Champion")
    s_champ_col = synergy_col_map["Champion"]
    synergy: Dict[str, Dict[str, float]] = {adc: {} for adc in pools["Adc_ally"]}
    for row in synergy_rows:
        if s_champ_col >= len(row):
            continue
        adc = row[s_champ_col]
        if adc not in synergy:
            continue
        for sup in pools["Sup_ally"]:
            idx = synergy_col_map.get(sup)
            if idx is None or idx >= len(row) or row[idx] == "":
                continue
            synergy[adc][sup] = float(row[idx])

    return DataModel(
        adc_ally=pools["Adc_ally"],
        sup_ally=pools["Sup_ally"],
        adc_meta=pools["Adc_meta"],
        sup_meta=pools["Sup_meta"],
        counter=counter,
        synergy=synergy,
        name_to_id=_load_name_to_id(champion_id_json_path),
    )
