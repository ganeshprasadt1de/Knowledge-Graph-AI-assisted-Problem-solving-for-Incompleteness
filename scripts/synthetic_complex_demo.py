from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


TRUE_TRIPLES = [
    ("Arch_Wall_101", "sameAs", "Struct_Wall_57"),
    ("Arch_Wall_102", "sameAs", "Struct_Wall_58"),
    ("Arch_Wall_103", "sameAs", "Struct_Wall_59"),
    ("Duct_22", "penetrates", "Struct_Wall_57"),
    ("Duct_23", "penetrates", "Struct_Beam_12"),
    ("Pipe_14", "penetrates", "Struct_Wall_58"),
    ("Duct_22", "requiresOpeningIn", "Struct_Wall_57"),
    ("Duct_23", "requiresOpeningIn", "Struct_Beam_12"),
    ("Pipe_14", "requiresOpeningIn", "Struct_Wall_58"),
]

HELD_OUT_TRIPLES = [
    ("Arch_Wall_101", "sameAs", "Struct_Wall_57"),
    ("Duct_22", "penetrates", "Struct_Wall_57"),
    ("Duct_22", "requiresOpeningIn", "Struct_Wall_57"),
]

NEGATIVE_CANDIDATES = [
    ("Arch_Wall_101", "sameAs", "Struct_Wall_59"),
    ("Duct_22", "penetrates", "Struct_Beam_12"),
    ("Duct_22", "requiresOpeningIn", "Struct_Wall_58"),
    ("Pipe_14", "penetrates", "Chair_01"),
    ("Window_08", "sameAs", "Struct_Beam_12"),
]


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

    return float(
        np.sum(
            h_re * r_re * t_re
            + h_re * r_im * t_im
            + h_im * r_re * t_im
            - h_im * r_im * t_re
        )
    )


def make_ids(triples: list[tuple[str, str, str]]) -> tuple[dict[str, int], dict[str, int]]:
    entities = sorted({item for triple in triples for item in (triple[0], triple[2])})
    relations = sorted({triple[1] for triple in triples})
    return {entity: index for index, entity in enumerate(entities)}, {
        relation: index for index, relation in enumerate(relations)
    }


def corrupt_tail(
    triple: tuple[str, str, str],
    entities: list[str],
    true_set: set[tuple[str, str, str]],
    rng: np.random.Generator,
) -> tuple[str, str, str]:
    head, relation, tail = triple
    while True:
        candidate = str(rng.choice(entities))
        negative = (head, relation, candidate)
        if candidate != tail and negative not in true_set:
            return negative


def train_complex(seed: int = 7, epochs: int = 350, dim: int = 24, learning_rate: float = 0.04) -> dict:
    rng = np.random.default_rng(seed)
    training_triples = list(TRUE_TRIPLES)
    all_triples = TRUE_TRIPLES + NEGATIVE_CANDIDATES
    entity_to_id, relation_to_id = make_ids(all_triples)
    id_to_entity = {value: key for key, value in entity_to_id.items()}
    true_set = set(TRUE_TRIPLES)
    entities = list(entity_to_id)

    scale = 0.08
    entity_re = rng.normal(0, scale, (len(entity_to_id), dim))
    entity_im = rng.normal(0, scale, (len(entity_to_id), dim))
    relation_re = rng.normal(0, scale, (len(relation_to_id), dim))
    relation_im = rng.normal(0, scale, (len(relation_to_id), dim))

    for _ in range(epochs):
        rng.shuffle(training_triples)
        for positive in training_triples:
            negative = corrupt_tail(positive, entities, true_set, rng)
            for triple, label in ((positive, 1.0), (negative, 0.0)):
                head, relation, tail = triple
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

                grad_h_re = r_re * t_re + r_im * t_im
                grad_h_im = r_re * t_im - r_im * t_re
                grad_r_re = h_re * t_re + h_im * t_im
                grad_r_im = h_re * t_im - h_im * t_re
                grad_t_re = h_re * r_re - h_im * r_im
                grad_t_im = h_re * r_im + h_im * r_re

                entity_re[h] -= learning_rate * error * grad_h_re
                entity_im[h] -= learning_rate * error * grad_h_im
                relation_re[r] -= learning_rate * error * grad_r_re
                relation_im[r] -= learning_rate * error * grad_r_im
                entity_re[t] -= learning_rate * error * grad_t_re
                entity_im[t] -= learning_rate * error * grad_t_im

        entity_re *= 0.999
        entity_im *= 0.999
        relation_re *= 0.999
        relation_im *= 0.999

    candidates = HELD_OUT_TRIPLES + NEGATIVE_CANDIDATES
    predictions = []
    for head, relation, tail in candidates:
        h = entity_to_id[head]
        r = relation_to_id[relation]
        t = entity_to_id[tail]
        raw_score = complex_score(entity_re, entity_im, relation_re, relation_im, h, r, t)
        predictions.append(
            {
                "triple": [head, relation, tail],
                "score": round(float(sigmoid(raw_score)), 3),
                "source": "synthetic_complex_demo",
            }
        )

    predictions.sort(key=lambda item: item["score"], reverse=True)

    return {
        "method": "ComplEx",
        "status": "trained_on_synthetic_data",
        "training_triples": [list(triple) for triple in training_triples],
        "demo_target_triples": [list(triple) for triple in HELD_OUT_TRIPLES],
        "negative_candidates": [list(triple) for triple in NEGATIVE_CANDIDATES],
        "entity_count": len(entity_to_id),
        "relation_count": len(relation_to_id),
        "embedding_dimension": dim,
        "epochs": epochs,
        "predictions": predictions,
        "note": "This demo proves the ComplEx workflow on artificial data. It is not trained on the real IFC-derived RDF graphs and is not an evaluation of generalization.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a small ComplEx model on synthetic building triples.")
    parser.add_argument("--output", type=Path, default=Path("outputs/05_synthetic_complex_predictions.json"))
    args = parser.parse_args()

    result = train_complex()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    for item in result["predictions"][:3]:
        head, relation, tail = item["triple"]
        print(f"({head}, {relation}, {tail}): {item['score']}")


if __name__ == "__main__":
    main()
