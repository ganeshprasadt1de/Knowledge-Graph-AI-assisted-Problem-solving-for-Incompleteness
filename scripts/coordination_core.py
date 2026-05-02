from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdflib import Graph, Namespace, RDF, RDFS, URIRef


BOT = Namespace("https://w3id.org/bot#")
BEO = Namespace("https://pi.pauwel.be/voc/buildingelement#")
IFC2X3 = Namespace("https://standards.buildingsmart.org/IFC/DEV/IFC2x3/TC1/OWL#")
IFC4 = Namespace("https://standards.buildingsmart.org/IFC/DEV/IFC4/ADD2/OWL#")
LBD = Namespace("https://linkebuildingdata.org/LBD#")
MEP = Namespace("https://pi.pauwel.be/voc/distributionelement#")
FURN = Namespace("http://pi.pauwel.be/voc/furniture#")
OMG = Namespace("https://w3id.org/omg#")
COORD = Namespace("https://example.org/coordination#")


RELATION_URIS = {
    "sameAs": COORD.sameAs,
    "isHostedBy": COORD.isHostedBy,
    "voidsElement": COORD.voidsElement,
    "penetrates": COORD.penetrates,
    "requiresOpeningIn": COORD.requiresOpeningIn,
}

STRUCTURAL_TYPES = {
    BEO.Wall,
    BEO.Beam,
    BEO.Column,
    BEO.Slab,
}

MEP_TYPES = {
    MEP.DuctSegment,
    MEP.DuctFitting,
    MEP.FlowTerminal,
}

OPENING_TYPES = {
    IFC2X3.IfcOpeningElement,
    IFC4.IfcOpeningElement,
}


@dataclass(frozen=True)
class Candidate:
    subject: str
    predicate: str
    object: str
    score: float
    method: str
    evidence: list[str]


@dataclass(frozen=True)
class BBox:
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float

    @property
    def volume(self) -> float:
        return max(0.0, self.xmax - self.xmin) * max(0.0, self.ymax - self.ymin) * max(0.0, self.zmax - self.zmin)


def load_graph(graph_uri: str | Path) -> Graph:
    path = Path(graph_uri).resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    graph = Graph()
    graph.parse(str(path), format="turtle")
    return graph


def label(graph: Graph, node: URIRef) -> str:
    value = graph.value(node, RDFS.label)
    return str(value) if value else str(node)


def has_type(graph: Graph, node: URIRef, rdf_type: URIRef) -> bool:
    return (node, RDF.type, rdf_type) in graph


def count_type(graph: Graph, rdf_type: URIRef) -> int:
    return sum(1 for _ in graph.subjects(RDF.type, rdf_type))


def inspect_graph(graph_uri: str | Path) -> dict[str, Any]:
    graph = load_graph(graph_uri)
    return {
        "triples": len(graph),
        "subjects": len(set(graph.subjects())),
        "predicates": len(set(graph.predicates())),
        "objects": len(set(graph.objects())),
        "bot_elements": count_type(graph, BOT.Element),
        "walls": count_type(graph, BEO.Wall),
        "doors": count_type(graph, BEO.Door),
        "windows": count_type(graph, BEO.Window),
        "opening_elements": sum(count_type(graph, rdf_type) for rdf_type in OPENING_TYPES),
        "flow_terminals": count_type(graph, MEP.FlowTerminal),
        "furniture": count_type(graph, FURN.Furniture),
        "storeys": count_type(graph, BOT.Storey),
        "geometry_links": sum(1 for _ in graph.triples((None, OMG.hasGeometry, None))),
        "bounding_box_links": sum(1 for _ in graph.triples((None, LBD.containsInBoundingBox, None))),
        "bot_subelement_links": sum(1 for _ in graph.triples((None, BOT.hasSubElement, None))),
    }


def inspect_profession_graphs(arc_graph_uri: str | Path, str_graph_uri: str | Path, mep_graph_uri: str | Path) -> dict[str, Any]:
    return {
        "architecture": inspect_graph(arc_graph_uri),
        "structure": inspect_graph(str_graph_uri),
        "mep": inspect_graph(mep_graph_uri),
    }


def _float_value(graph: Graph, subject: URIRef, predicate: URIRef) -> float | None:
    value = graph.value(subject, predicate)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _element_bbox(graph: Graph, element: URIRef) -> BBox | None:
    geometry = graph.value(element, OMG.hasGeometry)
    if geometry is None:
        return None
    bbox = graph.value(geometry, LBD.hasBoundingBox)
    if bbox is None:
        return None

    values = {
        "xmin": _float_value(graph, bbox, LBD["x-min"]),
        "xmax": _float_value(graph, bbox, LBD["x-max"]),
        "ymin": _float_value(graph, bbox, LBD["y-min"]),
        "ymax": _float_value(graph, bbox, LBD["y-max"]),
        "zmin": _float_value(graph, bbox, LBD["z-min"]),
        "zmax": _float_value(graph, bbox, LBD["z-max"]),
    }
    if any(value is None for value in values.values()):
        return None
    return BBox(**values)  # type: ignore[arg-type]


def _typed_elements_with_bbox(graph: Graph, types: set[URIRef]) -> list[tuple[URIRef, BBox]]:
    elements: list[tuple[URIRef, BBox]] = []
    for rdf_type in types:
        for element in graph.subjects(RDF.type, rdf_type):
            bbox = _element_bbox(graph, element)
            if bbox is not None:
                elements.append((element, bbox))
    return list(dict(elements).items())


def _intersection(a: BBox, b: BBox) -> BBox | None:
    bbox = BBox(
        xmin=max(a.xmin, b.xmin),
        xmax=min(a.xmax, b.xmax),
        ymin=max(a.ymin, b.ymin),
        ymax=min(a.ymax, b.ymax),
        zmin=max(a.zmin, b.zmin),
        zmax=min(a.zmax, b.zmax),
    )
    return bbox if bbox.volume > 0 else None


def _overlap_score(a: BBox, b: BBox) -> float:
    intersection = _intersection(a, b)
    if intersection is None:
        return 0.0
    base = min(a.volume, b.volume)
    if base <= 0:
        return 0.0
    return min(1.0, intersection.volume / base)


def find_cross_discipline_links(
    arc_graph_uri: str | Path,
    str_graph_uri: str | Path,
    mep_graph_uri: str | Path,
    target_relations: list[str] | None = None,
    method: str = "rule",
    limit: int = 25,
) -> dict[str, Any]:
    relations = set(target_relations or ["sameAs", "penetrates", "requiresOpeningIn"])

    if method in {"TransE", "RotatE", "ComplEx"}:
        return _embedding_not_trained(method) | {"candidates": []}
    if method != "rule":
        raise ValueError(f"Unsupported method: {method}")

    arc_graph = load_graph(arc_graph_uri)
    str_graph = load_graph(str_graph_uri)
    mep_graph = load_graph(mep_graph_uri)

    candidates: list[Candidate] = []
    arc_walls = _typed_elements_with_bbox(arc_graph, {BEO.Wall})
    str_structural = _typed_elements_with_bbox(str_graph, STRUCTURAL_TYPES)
    str_walls = _typed_elements_with_bbox(str_graph, {BEO.Wall})
    mep_elements = _typed_elements_with_bbox(mep_graph, MEP_TYPES)

    if "sameAs" in relations:
        for arc_wall, arc_bbox in arc_walls:
            for str_wall, str_bbox in str_walls:
                overlap = _overlap_score(arc_bbox, str_bbox)
                if overlap <= 0:
                    continue
                candidates.append(
                    Candidate(
                        subject=str(arc_wall),
                        predicate="sameAs",
                        object=str(str_wall),
                        score=round(min(0.95, 0.55 + overlap * 0.4), 3),
                        method="rule",
                        evidence=[
                            "architecture element is typed as beo:Wall",
                            "structure element is typed as beo:Wall",
                            "the two wall bounding boxes overlap across discipline graphs",
                            f"overlap ratio against smaller bounding box: {overlap:.3f}",
                        ],
                    )
                )

    if "penetrates" in relations or "requiresOpeningIn" in relations:
        for mep_element, mep_bbox in mep_elements:
            for structural_element, structural_bbox in str_structural:
                overlap = _overlap_score(mep_bbox, structural_bbox)
                if overlap <= 0:
                    continue
                base_evidence = [
                    "MEP element is typed as a duct, duct fitting, or flow terminal",
                    "structure element is typed as wall, beam, column, or slab",
                    "the MEP and structure bounding boxes overlap across discipline graphs",
                    f"overlap ratio against smaller bounding box: {overlap:.3f}",
                ]
                if "penetrates" in relations:
                    candidates.append(
                        Candidate(
                            subject=str(mep_element),
                            predicate="penetrates",
                            object=str(structural_element),
                            score=round(min(0.92, 0.5 + overlap * 0.42), 3),
                            method="rule",
                            evidence=base_evidence,
                        )
                    )
                if "requiresOpeningIn" in relations:
                    candidates.append(
                        Candidate(
                            subject=str(mep_element),
                            predicate="requiresOpeningIn",
                            object=str(structural_element),
                            score=round(min(0.88, 0.45 + overlap * 0.38), 3),
                            method="rule",
                            evidence=base_evidence
                            + ["penetration candidates usually require an opening or structural review"],
                        )
                    )

    candidates = sorted(candidates, key=lambda item: item.score, reverse=True)
    return {
        "method": method,
        "status": "ok",
        "candidate_count": len(candidates),
        "candidates": [candidate.__dict__ for candidate in candidates[:limit]],
    }


def _rule_candidates(graph: Graph, target_relations: set[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    for wall, element in graph.subject_objects(BOT.hasSubElement):
        if not has_type(graph, wall, BEO.Wall):
            continue

        if "voidsElement" in target_relations and any(has_type(graph, element, rdf_type) for rdf_type in OPENING_TYPES):
            candidates.append(
                Candidate(
                    subject=str(element),
                    predicate="voidsElement",
                    object=str(wall),
                    score=0.9,
                    method="rule",
                    evidence=[
                        "wall has bot:hasSubElement relation to an IfcOpeningElement",
                        "subject is typed as ifc:IfcOpeningElement",
                        "object is typed as beo:Wall",
                    ],
                )
            )

        if "isHostedBy" in target_relations and (
            has_type(graph, element, BEO.Window) or has_type(graph, element, BEO.Door)
        ):
            candidates.append(
                Candidate(
                    subject=str(element),
                    predicate="isHostedBy",
                    object=str(wall),
                    score=0.86,
                    method="rule",
                    evidence=[
                        "wall has bot:hasSubElement relation to a door or window",
                        "object is typed as beo:Wall",
                    ],
                )
            )

    for subject, obj in graph.subject_objects(LBD.containsInBoundingBox):
        if not has_type(graph, obj, BEO.Wall):
            continue

        if "penetrates" in target_relations and has_type(graph, subject, MEP.FlowTerminal):
            candidates.append(
                Candidate(
                    subject=str(subject),
                    predicate="penetrates",
                    object=str(obj),
                    score=0.72,
                    method="rule",
                    evidence=[
                        "subject is typed as mep:FlowTerminal",
                        "object is typed as beo:Wall",
                        "the graph contains lbd:containsInBoundingBox between the elements",
                    ],
                )
            )

        if "requiresOpeningIn" in target_relations and has_type(graph, subject, MEP.FlowTerminal):
            candidates.append(
                Candidate(
                    subject=str(subject),
                    predicate="requiresOpeningIn",
                    object=str(obj),
                    score=0.68,
                    method="rule",
                    evidence=[
                        "service element is spatially related to a wall",
                        "a service-wall penetration usually requires an opening review",
                    ],
                )
            )

    return candidates


def _embedding_not_trained(method: str) -> dict[str, Any]:
    return {
        "method": method,
        "status": "not_trained",
        "message": (
            f"{method} requires trained entity and relation embeddings. "
            "The current project has a small set of profession RDF graphs, which is enough for candidate generation "
            "but not enough for a defensible trained embedding model."
        ),
    }


def find_missing_coordination_links(
    graph_uri: str | Path,
    target_relations: list[str] | None = None,
    method: str = "rule",
    limit: int = 25,
) -> dict[str, Any]:
    graph = load_graph(graph_uri)
    relations = set(target_relations or RELATION_URIS.keys())

    if method in {"TransE", "RotatE", "ComplEx"}:
        return _embedding_not_trained(method) | {"candidates": []}
    if method != "rule":
        raise ValueError(f"Unsupported method: {method}")

    candidates = sorted(_rule_candidates(graph, relations), key=lambda item: item.score, reverse=True)
    return {
        "method": method,
        "status": "ok",
        "candidate_count": len(candidates),
        "candidates": [candidate.__dict__ for candidate in candidates[:limit]],
    }


def score_candidate_triple(
    graph_uri: str | Path,
    subject: str,
    predicate: str,
    object_: str,
    method: str = "rule",
) -> dict[str, Any]:
    if method in {"TransE", "RotatE", "ComplEx"}:
        return _embedding_not_trained(method) | {"score": None}
    if method != "rule":
        raise ValueError(f"Unsupported method: {method}")

    result = find_missing_coordination_links(graph_uri, [predicate], method="rule", limit=10_000)
    for candidate in result["candidates"]:
        if (
            candidate["subject"] == subject
            and candidate["predicate"] == predicate
            and candidate["object"] == object_
        ):
            return {
                "method": "rule",
                "status": "ok",
                "score": candidate["score"],
                "evidence": candidate["evidence"],
            }

    return {
        "method": "rule",
        "status": "ok",
        "score": 0.05,
        "evidence": ["no matching rule evidence was found in the graph"],
    }


def explain_candidate_link(
    graph_uri: str | Path,
    subject: str,
    predicate: str,
    object_: str,
    method: str = "rule",
) -> dict[str, Any]:
    return score_candidate_triple(graph_uri, subject, predicate, object_, method)


def export_rdf_patch(predictions: list[dict[str, Any]], threshold: float = 0.8) -> str:
    lines = [
        "@prefix coord: <https://example.org/coordination#> .",
        "",
    ]
    for item in predictions:
        if float(item.get("score", 0.0)) < threshold:
            continue
        predicate = item["predicate"]
        predicate_uri = RELATION_URIS.get(predicate, COORD[predicate])
        lines.append(f"<{item['subject']}> <{predicate_uri}> <{item['object']}> .")

    return "\n".join(lines) + "\n"
