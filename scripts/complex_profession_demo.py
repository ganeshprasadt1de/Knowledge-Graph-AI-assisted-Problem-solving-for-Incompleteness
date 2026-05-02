from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import unquote

import numpy as np

from coordination_core import find_cross_discipline_links


ROOT = Path(__file__).resolve().parents[1]
ARC_GRAPH = ROOT / "graphs" / "professions" / "arc_lbd.ttl"
STR_GRAPH = ROOT / "graphs" / "professions" / "str_lbd.ttl"
MEP_GRAPH = ROOT / "graphs" / "professions" / "mep_lbd.ttl"


def sigmoid(value: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-value))


def complex_score(
    entity_re: np.ndarray,
    entity_im: np.ndarray,
    relation_re: np.ndarray,
    relation_im: np.ndarray,
    head_id: int,
    relation_id: int,
    tail_id: int,
) -> float:
    h_re = entity_re[head_id]
    h_im = entity_im[head_id]
    r_re = relation_re[relation_id]
    r_im = relation_im[relation_id]
    t_re = entity_re[tail_id]
    t_im = entity_im[tail_id]
    return float(np.sum(h_re * r_re * t_re + h_re * r_im * t_im + h_im * r_re * t_im - h_im * r_im * t_re))


def short_name(uri: str, counters: dict[str, int], mapping: dict[str, str]) -> str:
    if "://" not in uri:
        return uri
    if uri in mapping:
        return mapping[uri]

    local = unquote(uri.rsplit("/", 1)[-1])
    prefix = local.split("_", 1)[0]
    category = {
        "ductfitting": "MEP_DuctFitting",
        "ductsegment": "MEP_DuctSegment",
        "flowterminal": "MEP_FlowTerminal",
        "beam": "Structural_Beam",
        "wall": "Structural_Wall" if "/str/" in uri else "Architectural_Wall",
        "column": "Structural_Column",
        "slab": "Structural_Slab",
    }.get(prefix, "Building_Element")

    counters[category] = counters.get(category, 0) + 1
    mapping[uri] = f"{category}_{counters[category]:02d}"
    return mapping[uri]


def make_ids(triples: list[tuple[str, str, str]]) -> tuple[dict[str, int], dict[str, int]]:
    entities = sorted({item for triple in triples for item in (triple[0], triple[2])})
    relations = sorted({triple[1] for triple in triples})
    return {entity: index for index, entity in enumerate(entities)}, {
        relation: index for index, relation in enumerate(relations)
    }


def generate_training_data(limit: int) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]], list[dict]]:
    result = find_cross_discipline_links(
        ARC_GRAPH,
        STR_GRAPH,
        MEP_GRAPH,
        target_relations=["sameAs", "penetrates", "requiresOpeningIn"],
        method="rule",
        limit=limit,
    )
    positives = [
        (item["subject"], item["predicate"], item["object"])
        for item in result["candidates"]
        if item["score"] >= 0.55
    ]

    tails_by_relation: dict[str, list[str]] = {}
    for _, relation, tail in positives:
        tails_by_relation.setdefault(relation, []).append(tail)

    true_set = set(positives)
    negatives: list[tuple[str, str, str]] = []
    for head, relation, tail in positives:
        for candidate_tail in tails_by_relation.get(relation, []):
            candidate = (head, relation, candidate_tail)
            if candidate_tail != tail and candidate not in true_set:
                negatives.append(candidate)
                break

    return positives, negatives, result["candidates"]


def train_complex(
    positives: list[tuple[str, str, str]],
    negatives: list[tuple[str, str, str]],
    seed: int = 11,
    dim: int = 48,
    epochs: int = 180,
    learning_rate: float = 0.018,
) -> dict:
    rng = np.random.default_rng(seed)
    all_triples = positives + negatives
    entity_to_id, relation_to_id = make_ids(all_triples)

    scale = 0.08
    entity_re = rng.normal(0, scale, (len(entity_to_id), dim))
    entity_im = rng.normal(0, scale, (len(entity_to_id), dim))
    relation_re = rng.normal(0, scale, (len(relation_to_id), dim))
    relation_im = rng.normal(0, scale, (len(relation_to_id), dim))

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

            score = complex_score(entity_re, entity_im, relation_re, relation_im, h, r, t)
            error = float(sigmoid(score) - label)

            entity_re[h] -= learning_rate * error * (r_re * t_re + r_im * t_im)
            entity_im[h] -= learning_rate * error * (r_re * t_im - r_im * t_re)
            relation_re[r] -= learning_rate * error * (h_re * t_re + h_im * t_im)
            relation_im[r] -= learning_rate * error * (h_re * t_im - h_im * t_re)
            entity_re[t] -= learning_rate * error * (h_re * r_re - h_im * r_im)
            entity_im[t] -= learning_rate * error * (h_re * r_im + h_im * r_re)

        entity_re *= 0.99
        entity_im *= 0.99
        relation_re *= 0.99
        relation_im *= 0.99

    return {
        "entity_to_id": entity_to_id,
        "relation_to_id": relation_to_id,
        "entity_re": entity_re,
        "entity_im": entity_im,
        "relation_re": relation_re,
        "relation_im": relation_im,
        "embedding_dimension": dim,
        "epochs": epochs,
    }


def score_triples(model: dict, triples: list[tuple[str, str, str]]) -> list[dict]:
    predictions = []
    for head, relation, tail in triples:
        h = model["entity_to_id"][head]
        r = model["relation_to_id"][relation]
        t = model["entity_to_id"][tail]
        raw = complex_score(model["entity_re"], model["entity_im"], model["relation_re"], model["relation_im"], h, r, t)
        predictions.append({"triple": [head, relation, tail], "score": round(float(sigmoid(raw)), 3)})
    return sorted(predictions, key=lambda item: item["score"], reverse=True)


def abstract_predictions(predictions: list[dict]) -> list[dict]:
    counters: dict[str, int] = {}
    mapping: dict[str, str] = {}
    abstract = []
    for item in predictions:
        head, relation, tail = item["triple"]
        abstract.append(
            {
                "triple": [
                    short_name(head, counters, mapping),
                    relation,
                    short_name(tail, counters, mapping),
                ],
                "score": item["score"],
            }
        )
    return abstract


def write_final_text(predictions: list[dict], target: Path) -> None:
    counters: dict[str, int] = {}
    mapping: dict[str, str] = {}
    lines = ["Predicted missing facts", ""]
    for item in predictions[:3]:
        head, relation, tail = item["triple"]
        head_name = short_name(head, counters, mapping)
        tail_name = short_name(tail, counters, mapping)
        lines.append(f"({head_name}, {relation}, {tail_name}): {item['score']}")

    lines.extend(
        [
            "",
            "Interpretation",
            "",
            "The number is a plausibility score.",
            "A higher score means the model considers the candidate fact more likely.",
            "",
            "Examples of coordination problems",
            "",
            "A duct goes through a beam.",
            "A pipe passes through a fire-rated wall without a proper opening.",
            "A structural column appears inside a room where the architect expected empty space.",
            "A ceiling is designed too low because MEP ducts need more space.",
            "An opening exists in the architectural model but not in the structural model.",
            "",
            "These are real design coordination problems.",
        ]
    )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_complex_profession_demo(output_json: Path | str, output_text: Path | str, limit: int = 300) -> dict:
    output_json = Path(output_json)
    output_text = Path(output_text)
    positives, negatives, source_candidates = generate_training_data(limit)
    model = train_complex(positives, negatives)
    raw_predictions = score_triples(model, positives[:20])
    predictions = abstract_predictions(raw_predictions)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "method": "ComplEx",
        "status": "trained_on_pseudo_labels_from_profession_graphs",
        "positive_training_triples": len(positives),
        "negative_training_triples": len(negatives),
        "source_graphs": [
            "graphs/professions/arc_lbd.ttl",
            "graphs/professions/str_lbd.ttl",
            "graphs/professions/mep_lbd.ttl",
        ],
        "source_candidate_count": len(source_candidates),
        "embedding_dimension": model["embedding_dimension"],
        "epochs": model["epochs"],
        "output_json": str(output_json),
        "output_text": str(output_text),
        "predictions": predictions,
        "note": "Training labels are generated from geometry/type rules on the three RDF graphs. They are pseudo-labels, not manually verified ground truth.",
    }
    output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_final_text(predictions, output_text)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a ComplEx demo on pseudo-labels from the profession RDF graphs.")
    parser.add_argument("--output-json", type=Path, default=ROOT / "outputs" / "05_complex_profession_predictions.json")
    parser.add_argument("--output-text", type=Path, default=ROOT / "outputs" / "00_final_demo_output.txt")
    parser.add_argument("--limit", type=int, default=300)
    args = parser.parse_args()

    result = run_complex_profession_demo(args.output_json, args.output_text, args.limit)

    for item in result["predictions"][:3]:
        head, relation, tail = item["triple"]
        print(f"({short_name(head, {}, {})}, {relation}, {short_name(tail, {}, {})}): {item['score']}")


if __name__ == "__main__":
    main()
