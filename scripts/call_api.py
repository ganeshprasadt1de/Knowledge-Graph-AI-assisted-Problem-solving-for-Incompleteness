from __future__ import annotations

import argparse
import json
from pathlib import Path

from coordination_core import (
    explain_candidate_link,
    export_rdf_patch,
    find_cross_discipline_links,
    find_missing_coordination_links,
    inspect_graph,
    inspect_profession_graphs,
    score_candidate_triple,
)
from complex_profession_demo import run_complex_profession_demo


def write_json(data) -> None:
    print(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Call the local coordination graph API.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("graph_uri", type=Path)

    inspect_professions_parser = subparsers.add_parser("inspect-professions")
    inspect_professions_parser.add_argument("arc_graph_uri", type=Path)
    inspect_professions_parser.add_argument("str_graph_uri", type=Path)
    inspect_professions_parser.add_argument("mep_graph_uri", type=Path)

    find_parser = subparsers.add_parser("find-links")
    find_parser.add_argument("graph_uri", type=Path)
    find_parser.add_argument("--method", default="rule", choices=["rule", "TransE", "RotatE", "ComplEx"])
    find_parser.add_argument("--limit", type=int, default=10)
    find_parser.add_argument(
        "--target-relation",
        action="append",
        dest="target_relations",
        help="May be repeated. Examples: isHostedBy, voidsElement, penetrates.",
    )

    cross_parser = subparsers.add_parser("find-cross-links")
    cross_parser.add_argument("arc_graph_uri", type=Path)
    cross_parser.add_argument("str_graph_uri", type=Path)
    cross_parser.add_argument("mep_graph_uri", type=Path)
    cross_parser.add_argument("--method", default="rule", choices=["rule", "TransE", "RotatE", "ComplEx"])
    cross_parser.add_argument("--limit", type=int, default=10)
    cross_parser.add_argument(
        "--target-relation",
        action="append",
        dest="target_relations",
        help="May be repeated. Examples: sameAs, penetrates, requiresOpeningIn.",
    )

    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("graph_uri", type=Path)
    score_parser.add_argument("subject")
    score_parser.add_argument("predicate")
    score_parser.add_argument("object_")
    score_parser.add_argument("--method", default="rule", choices=["rule", "TransE", "RotatE", "ComplEx"])

    explain_parser = subparsers.add_parser("explain")
    explain_parser.add_argument("graph_uri", type=Path)
    explain_parser.add_argument("subject")
    explain_parser.add_argument("predicate")
    explain_parser.add_argument("object_")
    explain_parser.add_argument("--method", default="rule", choices=["rule", "TransE", "RotatE", "ComplEx"])

    patch_parser = subparsers.add_parser("export-patch")
    patch_parser.add_argument("predictions_json", type=Path)
    patch_parser.add_argument("--threshold", type=float, default=0.8)

    complex_parser = subparsers.add_parser("complex-profession-demo")
    complex_parser.add_argument("--output-json", type=Path, default=Path("outputs/05_complex_profession_predictions.json"))
    complex_parser.add_argument("--output-text", type=Path, default=Path("outputs/00_final_demo_output.txt"))
    complex_parser.add_argument("--limit", type=int, default=300)

    args = parser.parse_args()

    if args.command == "inspect":
        write_json(inspect_graph(args.graph_uri))
    elif args.command == "inspect-professions":
        write_json(inspect_profession_graphs(args.arc_graph_uri, args.str_graph_uri, args.mep_graph_uri))
    elif args.command == "find-links":
        write_json(
            find_missing_coordination_links(
                args.graph_uri,
                target_relations=args.target_relations,
                method=args.method,
                limit=args.limit,
            )
        )
    elif args.command == "find-cross-links":
        write_json(
            find_cross_discipline_links(
                args.arc_graph_uri,
                args.str_graph_uri,
                args.mep_graph_uri,
                target_relations=args.target_relations,
                method=args.method,
                limit=args.limit,
            )
        )
    elif args.command == "score":
        write_json(score_candidate_triple(args.graph_uri, args.subject, args.predicate, args.object_, args.method))
    elif args.command == "explain":
        write_json(explain_candidate_link(args.graph_uri, args.subject, args.predicate, args.object_, args.method))
    elif args.command == "export-patch":
        predictions = json.loads(args.predictions_json.read_text(encoding="utf-8"))
        print(export_rdf_patch(predictions, args.threshold))
    elif args.command == "complex-profession-demo":
        write_json(run_complex_profession_demo(args.output_json, args.output_text, args.limit))


if __name__ == "__main__":
    main()
