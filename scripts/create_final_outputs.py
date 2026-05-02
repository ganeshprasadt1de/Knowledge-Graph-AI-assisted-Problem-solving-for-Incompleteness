from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote

from coordination_core import find_cross_discipline_links, inspect_profession_graphs


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
ARC_GRAPH = ROOT / "graphs" / "professions" / "arc_lbd.ttl"
STR_GRAPH = ROOT / "graphs" / "professions" / "str_lbd.ttl"
MEP_GRAPH = ROOT / "graphs" / "professions" / "mep_lbd.ttl"


def short_name(uri: str, counters: dict[str, int], mapping: dict[str, str]) -> str:
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
        "window": "Architectural_Window",
        "door": "Architectural_Door",
    }.get(prefix, "Building_Element")

    counters[category] = counters.get(category, 0) + 1
    mapping[uri] = f"{category}_{counters[category]:02d}"
    return mapping[uri]


def abstract_candidates(data: dict, target: Path, limit: int = 10) -> None:
    counters: dict[str, int] = {}
    mapping: dict[str, str] = {}

    candidates = []
    for item in data.get("candidates", [])[:limit]:
        subject = short_name(item["subject"], counters, mapping)
        object_ = short_name(item["object"], counters, mapping)
        candidates.append(
            {
                "triple": [subject, item["predicate"], object_],
                "score": item["score"],
                "evidence": item.get("evidence", []),
            }
        )

    abstract = {
        "method": data.get("method"),
        "status": data.get("status"),
        "candidate_count": data.get("candidate_count"),
        "candidates": candidates,
    }
    target.write_text(json.dumps(abstract, indent=2), encoding="utf-8")


def abstract_inspection(data: dict, target: Path) -> None:
    abstract = {
        "architecture_graph": {
            "triples": data["architecture"]["triples"],
            "walls": data["architecture"]["walls"],
            "doors": data["architecture"]["doors"],
            "windows": data["architecture"]["windows"],
            "opening_elements": data["architecture"]["opening_elements"],
        },
        "structure_graph": {
            "triples": data["structure"]["triples"],
            "walls": data["structure"]["walls"],
            "geometry_links": data["structure"]["geometry_links"],
        },
        "mep_graph": {
            "triples": data["mep"]["triples"],
            "flow_terminals": data["mep"]["flow_terminals"],
            "geometry_links": data["mep"]["geometry_links"],
        },
    }
    target.write_text(json.dumps(abstract, indent=2), encoding="utf-8")


def final_text(complex_source: Path, target: Path) -> None:
    data = json.loads(complex_source.read_text(encoding="utf-8-sig"))
    lines = [
        "Predicted missing facts",
        "",
    ]
    for item in data["predictions"][:3]:
        head, relation, tail = item["triple"]
        lines.append(f"({head}, {relation}, {tail}): {item['score']}")

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


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    inspection = inspect_profession_graphs(ARC_GRAPH, STR_GRAPH, MEP_GRAPH)
    penetration_candidates = find_cross_discipline_links(
        ARC_GRAPH,
        STR_GRAPH,
        MEP_GRAPH,
        target_relations=["penetrates", "requiresOpeningIn"],
        limit=10,
    )
    sameas_candidates = find_cross_discipline_links(
        ARC_GRAPH,
        STR_GRAPH,
        MEP_GRAPH,
        target_relations=["sameAs"],
        limit=10,
    )

    abstract_inspection(
        inspection,
        OUTPUT_DIR / "01_graph_summary_abstract.json",
    )
    abstract_candidates(
        penetration_candidates,
        OUTPUT_DIR / "02_penetration_candidates_abstract.json",
    )
    abstract_candidates(
        sameas_candidates,
        OUTPUT_DIR / "03_sameas_candidates_abstract.json",
    )
    final_text(
        OUTPUT_DIR / "05_synthetic_complex_predictions.json",
        OUTPUT_DIR / "00_final_demo_output.txt",
    )


if __name__ == "__main__":
    main()
