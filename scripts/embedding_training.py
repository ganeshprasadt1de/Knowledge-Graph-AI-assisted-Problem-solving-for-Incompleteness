from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import numpy as np

from coordination_core import find_cross_discipline_links


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "datasets" / "BIM Spatial Models for Construction Dependency Inf"
MODEL_DIR = ROOT / "models"
OUTPUT_DIR = ROOT / "outputs"
ARC_GRAPH = ROOT / "graphs" / "professions" / "arc_lbd.ttl"
STR_GRAPH = ROOT / "graphs" / "professions" / "str_lbd.ttl"
MEP_GRAPH = ROOT / "graphs" / "professions" / "mep_lbd.ttl"


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, value))))


def clean_token(value: str) -> str:
    result = "".join(char.lower() if char.isalnum() else "_" for char in value)
    return "_".join(part for part in result.split("_") if part)


def element_type(name: str) -> str:
    lowered = name.lower()
    checks = [
        ("Service_Element", ["duct", "风管", "pipe", "管道", "水管"]),
        ("Door", ["door", "门"]),
        ("Window", ["window", "窗"]),
        ("Wall", ["wall", "墙", "基本墙"]),
        ("Beam", ["beam", "梁"]),
        ("Column", ["column", "柱"]),
        ("Slab", ["slab", "floor", "楼板", "板"]),
        ("Furniture", ["furniture", "desk", "chair", "家具", "桌", "椅"]),
        ("Opening", ["opening", "洞口"]),
        ("Stair", ["stair", "楼梯"]),
        ("Space", ["space", "room", "房间"]),
    ]
    for label, keywords in checks:
        if any(keyword in lowered or keyword in name for keyword in keywords):
            return label
    return "Building_Element"


def relation_tokens(value: str) -> list[str]:
    tokens = []
    for part in value.split(","):
        token = clean_token(part.strip())
        if token:
            tokens.append(token)
    return tokens


def read_positive_type_triples(
    dataset_dir: Path,
    max_rows: int | None = None,
    max_repeats_per_pattern: int = 80,
) -> list[tuple[str, str, str]]:
    triples: list[tuple[str, str, str]] = []
    pattern_counts: dict[tuple[str, str, str], int] = {}
    for csv_path in sorted(dataset_dir.rglob("spatial_relationships_detailed.csv")):
        project = clean_token(csv_path.parent.name)
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                head_type = element_type(row["name1"])
                tail_type = element_type(row["name2"])
                for relation in relation_tokens(row["relation"]):
                    triple = (f"{project}:{head_type}", relation, f"{project}:{tail_type}")
                    pattern_counts[triple] = pattern_counts.get(triple, 0) + 1
                    if pattern_counts[triple] <= max_repeats_per_pattern:
                        triples.append(triple)
                if max_rows and len(triples) >= max_rows:
                    return triples
    return triples


def make_negative_triples(
    positives: list[tuple[str, str, str]],
    negatives_per_positive: int = 1,
    seed: int = 7,
) -> list[tuple[str, str, str]]:
    rng = np.random.default_rng(seed)
    true_set = set(positives)
    tails_by_project: dict[str, list[str]] = {}
    for _, _, tail in positives:
        project = tail.split(":", 1)[0]
        tails_by_project.setdefault(project, []).append(tail)

    negatives: list[tuple[str, str, str]] = []
    for head, relation, tail in positives:
        project = head.split(":", 1)[0]
        tail_pool = tails_by_project.get(project, [])
        if not tail_pool:
            continue
        for _ in range(negatives_per_positive):
            for _ in range(25):
                corrupt_tail = str(rng.choice(tail_pool))
                candidate = (head, relation, corrupt_tail)
                if corrupt_tail != tail and candidate not in true_set:
                    negatives.append(candidate)
                    break
    return negatives


def make_ids(triples: list[tuple[str, str, str]]) -> tuple[dict[str, int], dict[str, int]]:
    entities = sorted({item for triple in triples for item in (triple[0], triple[2])})
    relations = sorted({triple[1] for triple in triples})
    return {entity: index for index, entity in enumerate(entities)}, {
        relation: index for index, relation in enumerate(relations)
    }


def type_pattern_key(head: str, relation: str, tail: str) -> str:
    head_type = head.split(":", 1)[-1]
    tail_type = tail.split(":", 1)[-1]
    return f"{head_type}|{relation}|{tail_type}"


def build_pattern_counts(positives: list[tuple[str, str, str]]) -> dict[str, Any]:
    pattern_counts: dict[str, int] = {}
    relation_counts: dict[str, int] = {}
    for head, relation, tail in positives:
        key = type_pattern_key(head, relation, tail)
        pattern_counts[key] = pattern_counts.get(key, 0) + 1
        relation_counts[relation] = relation_counts.get(relation, 0) + 1
    return {
        "type_pattern_counts": pattern_counts,
        "relation_counts": relation_counts,
    }


def train_embedding(
    positives: list[tuple[str, str, str]],
    negatives: list[tuple[str, str, str]],
    method: str,
    dim: int = 48,
    epochs: int = 120,
    learning_rate: float = 0.025,
    seed: int = 11,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    all_triples = positives + negatives
    entity_to_id, relation_to_id = make_ids(all_triples)

    entity_re = rng.normal(0, 0.08, (len(entity_to_id), dim))
    entity_im = rng.normal(0, 0.08, (len(entity_to_id), dim))
    relation_re = rng.normal(0, 0.08, (len(relation_to_id), dim))
    relation_im = rng.normal(0, 0.08, (len(relation_to_id), dim))

    labeled = [(triple, 1.0) for triple in positives] + [(triple, 0.0) for triple in negatives]
    for _ in range(epochs):
        rng.shuffle(labeled)
        for (head, relation, tail), label in labeled:
            h = entity_to_id[head]
            r = relation_to_id[relation]
            t = entity_to_id[tail]

            h_re = entity_re[h].copy()
            h_im = entity_im[h].copy()
            r_re = relation_re[r].copy()
            r_im = relation_im[r].copy()
            t_re = entity_re[t].copy()
            t_im = entity_im[t].copy()

            raw = score_raw(method, entity_re, entity_im, relation_re, relation_im, h, r, t)
            error = sigmoid(raw) - label

            if method == "TransE":
                direction = h_re + r_re - t_re
                entity_re[h] -= learning_rate * error * direction
                relation_re[r] -= learning_rate * error * direction
                entity_re[t] += learning_rate * error * direction
            elif method == "RotatE":
                pred_re = h_re * r_re - h_im * r_im
                pred_im = h_re * r_im + h_im * r_re
                diff_re = pred_re - t_re
                diff_im = pred_im - t_im
                entity_re[h] -= learning_rate * error * (diff_re * r_re + diff_im * r_im)
                entity_im[h] -= learning_rate * error * (-diff_re * r_im + diff_im * r_re)
                relation_re[r] -= learning_rate * error * (diff_re * h_re + diff_im * h_im)
                relation_im[r] -= learning_rate * error * (-diff_re * h_im + diff_im * h_re)
                entity_re[t] += learning_rate * error * diff_re
                entity_im[t] += learning_rate * error * diff_im
            else:
                entity_re[h] -= learning_rate * error * (r_re * t_re + r_im * t_im)
                entity_im[h] -= learning_rate * error * (r_re * t_im - r_im * t_re)
                relation_re[r] -= learning_rate * error * (h_re * t_re + h_im * t_im)
                relation_im[r] -= learning_rate * error * (h_re * t_im - h_im * t_re)
                entity_re[t] -= learning_rate * error * (h_re * r_re - h_im * r_im)
                entity_im[t] -= learning_rate * error * (h_re * r_im + h_im * r_re)

        entity_re *= 0.995
        entity_im *= 0.995
        relation_re *= 0.995
        relation_im *= 0.995

    return {
        "method": method,
        "entity_to_id": entity_to_id,
        "relation_to_id": relation_to_id,
        "entity_re": entity_re.tolist(),
        "entity_im": entity_im.tolist(),
        "relation_re": relation_re.tolist(),
        "relation_im": relation_im.tolist(),
        "embedding_dimension": dim,
        "epochs": epochs,
        "positive_training_triples": len(positives),
        "negative_training_triples": len(negatives),
    }


def score_raw(
    method: str,
    entity_re: np.ndarray,
    entity_im: np.ndarray,
    relation_re: np.ndarray,
    relation_im: np.ndarray,
    h: int,
    r: int,
    t: int,
) -> float:
    h_re = entity_re[h]
    h_im = entity_im[h]
    r_re = relation_re[r]
    r_im = relation_im[r]
    t_re = entity_re[t]
    t_im = entity_im[t]
    if method == "TransE":
        return float(4.0 - np.linalg.norm(h_re + r_re - t_re))
    if method == "RotatE":
        pred_re = h_re * r_re - h_im * r_im
        pred_im = h_re * r_im + h_im * r_re
        return float(4.0 - np.linalg.norm(pred_re - t_re) - np.linalg.norm(pred_im - t_im))
    return float(np.sum(h_re * r_re * t_re + h_re * r_im * t_im + h_im * r_re * t_im - h_im * r_im * t_re))


def save_model(model: dict[str, Any], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(model, indent=2), encoding="utf-8")


def load_model(path: Path) -> dict[str, Any]:
    model = json.loads(path.read_text(encoding="utf-8"))
    for key in ("entity_re", "entity_im", "relation_re", "relation_im"):
        model[key] = np.array(model[key], dtype=float)
    return model


def project_entity_type(uri: str) -> str:
    local = unquote(uri.rsplit("/", 1)[-1]).lower()
    if "duct" in local or "flowterminal" in local or "pipe" in local:
        return "Service_Element"
    if "beam" in local:
        return "Beam"
    if "wall" in local:
        return "Wall"
    if "column" in local:
        return "Column"
    if "slab" in local:
        return "Slab"
    if "door" in local:
        return "Door"
    if "window" in local:
        return "Window"
    return "Building_Element"


def abstract_name(uri: str, counters: dict[str, int], mapping: dict[str, str]) -> str:
    if uri in mapping:
        return mapping[uri]
    category = {
        "Service_Element": "MEP_Duct",
        "Beam": "Structural_Beam",
        "Wall": "Architectural_Wall" if "/arc/" in uri else "Structural_Wall",
        "Column": "Structural_Column",
        "Slab": "Structural_Slab",
        "Door": "Architectural_Door",
        "Window": "Architectural_Window",
    }.get(project_entity_type(uri), "Building_Element")
    counters[category] = counters.get(category, 0) + 1
    mapping[uri] = f"{category}_{counters[category]:02d}"
    return mapping[uri]


def relation_for_candidate(predicate: str) -> str:
    if predicate in {"penetrates", "requiresOpeningIn"}:
        return "partially_embedded"
    if predicate == "sameAs":
        return "face_overlap"
    return clean_token(predicate)


def support_for_type_pattern(model: dict[str, Any], head_type: str, relation: str, tail_type: str) -> dict[str, Any]:
    pattern_counts = model.get("type_pattern_counts", {})
    relation_counts = model.get("relation_counts", {})
    exact_key = f"{head_type}|{relation}|{tail_type}"
    exact_count = int(pattern_counts.get(exact_key, 0))
    relation_total = max(1, int(relation_counts.get(relation, 0)))

    backoff_keys = [
        f"{head_type}|{relation}|Building_Element",
        f"Building_Element|{relation}|{tail_type}",
    ]
    backoff_matches = [(key, int(pattern_counts.get(key, 0))) for key in backoff_keys]
    backoff_key, backoff_count = max(backoff_matches, key=lambda item: item[1])

    if exact_count > 0:
        level = "direct"
        support_count = exact_count
        support_key = exact_key
        support_weight = 1.0
    elif backoff_count > 0:
        level = "backoff"
        support_count = backoff_count
        support_key = backoff_key
        support_weight = 0.45
    else:
        level = "none"
        support_count = 0
        support_key = exact_key
        support_weight = 0.0

    support_score = support_weight * min(1.0, math.log1p(support_count) / math.log1p(relation_total))
    return {
        "support_level": level,
        "support_count": support_count,
        "support_pattern": support_key,
        "support_score": round(support_score, 3),
    }


def score_type_triple(model: dict[str, Any], head_type: str, relation: str, tail_type: str) -> dict[str, Any]:
    entity_to_id = model["entity_to_id"]
    relation_to_id = model["relation_to_id"]
    candidates = [
        (entity, entity_to_id[entity])
        for entity in entity_to_id
        if entity.endswith(f":{head_type}")
    ]
    tails = [
        (entity, entity_to_id[entity])
        for entity in entity_to_id
        if entity.endswith(f":{tail_type}")
    ]
    support = support_for_type_pattern(model, head_type, relation, tail_type)
    if relation not in relation_to_id or not candidates or not tails:
        return {"embedding_score": 0.05, **support}

    r = relation_to_id[relation]
    scores = []
    for _, h in candidates:
        for _, t in tails:
            raw = score_raw(model["method"], model["entity_re"], model["entity_im"], model["relation_re"], model["relation_im"], h, r, t)
            scores.append(sigmoid(raw))
    return {"embedding_score": float(sum(scores) / len(scores)), **support}


def train_from_dataset(
    dataset_dir: Path | str = DATASET_DIR,
    method: str = "ComplEx",
    output_model: Path | str = MODEL_DIR / "bim_spatial_complex_model.json",
    max_rows: int | None = None,
) -> dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    output_model = Path(output_model)
    positives = read_positive_type_triples(dataset_dir, max_rows)
    negatives = make_negative_triples(positives)
    model = train_embedding(positives, negatives, method)
    model.update(build_pattern_counts(positives))
    model["dataset_dir"] = str(dataset_dir)
    model["training_note"] = (
        "Positive triples come from public BIM spatial relationship CSV files. "
        "Negative triples are generated by replacing the tail element type within the same project."
    )
    save_model(model, output_model)
    return {
        "method": method,
        "model_path": str(output_model),
        "positive_training_triples": len(positives),
        "negative_training_triples": len(negatives),
        "entity_count": len(model["entity_to_id"]),
        "relation_count": len(model["relation_to_id"]),
        "relations": sorted(model["relation_to_id"]),
    }


def create_coordination_report(
    model_path: Path | str,
    output_text: Path | str,
    output_json: Path | str,
    arc_graph: Path | str = ARC_GRAPH,
    str_graph: Path | str = STR_GRAPH,
    mep_graph: Path | str = MEP_GRAPH,
    limit: int = 12,
) -> dict[str, Any]:
    model_path = Path(model_path)
    output_text = Path(output_text)
    output_json = Path(output_json)
    arc_graph = Path(arc_graph)
    str_graph = Path(str_graph)
    mep_graph = Path(mep_graph)
    model = load_model(model_path)
    candidates = find_cross_discipline_links(
        arc_graph,
        str_graph,
        mep_graph,
        target_relations=["sameAs", "penetrates", "requiresOpeningIn"],
        method="rule",
        limit=400,
    )["candidates"]

    counters: dict[str, int] = {}
    mapping: dict[str, str] = {}
    report_items = []
    for item in candidates:
        head_type = project_entity_type(item["subject"])
        tail_type = project_entity_type(item["object"])
        relation = relation_for_candidate(item["predicate"])
        model_evidence = score_type_triple(model, head_type, relation, tail_type)
        embedding_score = float(model_evidence["embedding_score"])
        support_score = float(model_evidence["support_score"])
        geometry_score = float(item["score"])
        combined = round((0.75 * geometry_score) + (0.15 * embedding_score) + (0.10 * support_score), 3)
        if geometry_score >= 0.6 and model_evidence["support_level"] != "none":
            risk_level = "high"
        elif geometry_score >= 0.55:
            risk_level = "medium"
        else:
            risk_level = "low"
        report_items.append(
            {
                "subject": abstract_name(item["subject"], counters, mapping),
                "predicate": item["predicate"],
                "object": abstract_name(item["object"], counters, mapping),
                "score": combined,
                "risk_level": risk_level,
                "geometry_score": round(geometry_score, 3),
                "embedding_score": round(embedding_score, 3),
                "dataset_support_level": model_evidence["support_level"],
                "dataset_support_count": model_evidence["support_count"],
                "dataset_support_pattern": model_evidence["support_pattern"],
                "dataset_support_score": model_evidence["support_score"],
                "evidence": item["evidence"],
            }
        )

    all_report_items = sorted(report_items, key=lambda row: row["score"], reverse=True)
    report_items = all_report_items[:limit]
    result = {
        "model_path": str(model_path),
        "method": model["method"],
        "training_source": model.get("dataset_dir"),
        "project_graphs": [str(arc_graph), str(str_graph), str(mep_graph)],
        "candidate_count": len(all_report_items),
        "report_items": report_items,
        "all_candidates": all_report_items,
        "note": "Scores combine geometric overlap from the three RDF graphs with an embedding score trained on public BIM spatial relationship data.",
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_text.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = ["Coordination Problems To Review", ""]
    for index, item in enumerate(report_items, start=1):
        lines.append(f"{index}. {item['subject']} {item['predicate']} {item['object']}")
        lines.append(f"Score: {item['score']}")
        lines.append(f"Risk level: {item['risk_level']}")
        lines.append(
            "Reason: "
            f"geometry score {item['geometry_score']}, "
            f"embedding score {item['embedding_score']}, "
            f"dataset support {item['dataset_support_level']} ({item['dataset_support_count']} examples)"
        )
        lines.append("")
    lines.append(f"Total candidates checked: {len(all_report_items)}")
    lines.append("The report is a ranked review list. It is not an automatic construction decision.")
    output_text.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Train embedding models from BIM spatial relationship data.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--dataset", type=Path, default=DATASET_DIR)
    train_parser.add_argument("--method", choices=["ComplEx", "TransE", "RotatE"], default="ComplEx")
    train_parser.add_argument("--output-model", type=Path, default=MODEL_DIR / "bim_spatial_complex_model.json")
    train_parser.add_argument("--max-rows", type=int)

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--model", type=Path, default=MODEL_DIR / "bim_spatial_complex_model.json")
    report_parser.add_argument("--output-text", type=Path, default=OUTPUT_DIR / "coordination_report.txt")
    report_parser.add_argument("--output-json", type=Path, default=OUTPUT_DIR / "coordination_report.json")
    report_parser.add_argument("--limit", type=int, default=12)

    args = parser.parse_args()
    if args.command == "train":
        print(json.dumps(train_from_dataset(args.dataset, args.method, args.output_model, args.max_rows), indent=2))
    elif args.command == "report":
        print(json.dumps(create_coordination_report(args.model, args.output_text, args.output_json, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
