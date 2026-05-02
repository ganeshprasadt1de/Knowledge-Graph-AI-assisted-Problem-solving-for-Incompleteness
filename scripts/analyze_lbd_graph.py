from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from rdflib import Graph, Namespace, RDF, RDFS


BOT = Namespace("https://w3id.org/bot#")
BEO = Namespace("https://pi.pauwel.be/voc/buildingelement#")
IFC2X3 = Namespace("https://standards.buildingsmart.org/IFC/DEV/IFC2x3/TC1/OWL#")
IFC4 = Namespace("https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2/OWL#")
LBD = Namespace("https://linkebuildingdata.org/LBD#")
MEP = Namespace("https://pi.pauwel.be/voc/distributionelement#")
FURN = Namespace("http://pi.pauwel.be/voc/furniture#")
OMG = Namespace("https://w3id.org/omg#")


def label(graph: Graph, node) -> str:
    value = graph.value(node, RDFS.label)
    return str(value) if value else str(node)


def count_type(graph: Graph, rdf_type) -> int:
    return sum(1 for _ in graph.subjects(RDF.type, rdf_type))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize an IFCtoLBD Turtle graph for the Task 3 write-up."
    )
    parser.add_argument("ttl_file", type=Path)
    args = parser.parse_args()

    ttl_file = args.ttl_file.resolve()
    if not ttl_file.exists():
        raise FileNotFoundError(ttl_file)

    graph = Graph()
    graph.parse(str(ttl_file), format="turtle")

    print("Graph summary")
    print(f"Triples: {len(graph)}")
    print(f"Subjects: {len(set(graph.subjects()))}")
    print(f"Predicates: {len(set(graph.predicates()))}")
    print(f"Objects: {len(set(graph.objects()))}")
    print()

    type_counts = {
        "BOT elements": count_type(graph, BOT.Element),
        "Walls": count_type(graph, BEO.Wall),
        "Doors": count_type(graph, BEO.Door),
        "Windows": count_type(graph, BEO.Window),
        "IFC opening elements": count_type(graph, IFC2X3.IfcOpeningElement) + count_type(graph, IFC4.IfcOpeningElement),
        "Flow terminals": count_type(graph, MEP.FlowTerminal),
        "Furniture": count_type(graph, FURN.Furniture),
        "Storeys": count_type(graph, BOT.Storey),
        "Geometry links": sum(1 for _ in graph.triples((None, OMG.hasGeometry, None))),
        "Bounding-box containment links": sum(
            1 for _ in graph.triples((None, LBD.containsInBoundingBox, None))
        ),
        "BOT subelement links": sum(1 for _ in graph.triples((None, BOT.hasSubElement, None))),
    }

    print("Selected type and relation counts")
    for name, count in type_counts.items():
        print(f"{name}: {count}")
    print()

    print("Most common RDF classes")
    for rdf_type, count in Counter(graph.objects(None, RDF.type)).most_common(12):
        print(f"{count}: {rdf_type}")
    print()

    print("Sample wall-to-subelement links")
    for index, (wall, element) in enumerate(graph.subject_objects(BOT.hasSubElement), start=1):
        print(f"{index}. {label(graph, wall)} -> {label(graph, element)}")
        if index == 12:
            break


if __name__ == "__main__":
    main()
