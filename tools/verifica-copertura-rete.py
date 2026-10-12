#!/usr/bin/env python3
"""Confronta il perimetro censito con tutti i nodi della topologia di rete."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--matrice",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data/copertura-rete-20261008.json",
    )
    parser.add_argument("--topologia", required=True, type=Path)
    args = parser.parse_args()

    matrix = json.loads(args.matrice.read_text(encoding="utf-8-sig"))
    topology = json.loads(args.topologia.read_text(encoding="utf-8-sig"))
    ids = [item for group in matrix["gruppi"] for item in group["ids"]]
    topo_ids = [node["id"] for node in topology["nodi"]]
    outside_ids = [item["id"] for item in matrix.get("asset_documentati_fuori_topologia", [])]
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    topo_duplicates = sorted(item for item, count in Counter(topo_ids).items() if count > 1)
    outside_duplicates = sorted(item for item, count in Counter(outside_ids).items() if count > 1)
    outside_overlap = sorted(set(outside_ids) & set(topo_ids))
    missing = sorted(set(topo_ids) - set(ids))
    stale = sorted(set(ids) - set(topo_ids))
    if duplicates or topo_duplicates or missing or stale or outside_duplicates or outside_overlap:
        print(
            f"duplicati={duplicates} duplicati_topologia={topo_duplicates} "
            f"mancanti={missing} non_presenti={stale} "
            f"duplicati_fuori_topologia={outside_duplicates} gia_censiti={outside_overlap}"
        )
        return 1
    print(
        f"copertura inventario: {len(ids)}/{len(topo_ids)} nodi topologici; "
        f"{len(outside_ids)} asset documentati fuori topologia"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
