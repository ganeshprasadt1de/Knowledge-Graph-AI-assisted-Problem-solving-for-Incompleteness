from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from coordination_core import (
    explain_candidate_link as explain_candidate_link_backend,
    export_rdf_patch,
    find_cross_discipline_links as find_cross_discipline_links_backend,
    find_missing_coordination_links as find_missing_coordination_links_backend,
    inspect_graph,
    inspect_profession_graphs as inspect_profession_graphs_backend,
    score_candidate_triple as score_candidate_triple_backend,
)
from complex_profession_demo import run_complex_profession_demo


mcp = FastMCP("building-coordination-kg")


@mcp.tool()
def inspect_lbd_graph(graph_uri: str) -> dict:
    """Return counts for the IFCtoLBD RDF graph."""
    return inspect_graph(graph_uri)


@mcp.tool()
def inspect_profession_graphs(arc_graph_uri: str, str_graph_uri: str, mep_graph_uri: str) -> dict:
    """Return counts for architecture, structure, and MEP RDF graphs."""
    return inspect_profession_graphs_backend(arc_graph_uri, str_graph_uri, mep_graph_uri)


@mcp.tool()
def find_missing_coordination_links(
    graph_uri: str,
    target_relations: list[str] | None = None,
    method: str = "rule",
    limit: int = 25,
) -> dict:
    """Return candidate missing coordination triples."""
    return find_missing_coordination_links_backend(graph_uri, target_relations, method, limit)


@mcp.tool()
def find_cross_discipline_links(
    arc_graph_uri: str,
    str_graph_uri: str,
    mep_graph_uri: str,
    target_relations: list[str] | None = None,
    method: str = "rule",
    limit: int = 25,
) -> dict:
    """Return candidate links across architecture, structure, and MEP graphs."""
    return find_cross_discipline_links_backend(
        arc_graph_uri,
        str_graph_uri,
        mep_graph_uri,
        target_relations,
        method,
        limit,
    )


@mcp.tool()
def score_candidate_triple(
    graph_uri: str,
    subject: str,
    predicate: str,
    object_: str,
    method: str = "rule",
) -> dict:
    """Score one candidate coordination triple."""
    return score_candidate_triple_backend(graph_uri, subject, predicate, object_, method)


@mcp.tool()
def explain_candidate_link(
    graph_uri: str,
    subject: str,
    predicate: str,
    object_: str,
    method: str = "rule",
) -> dict:
    """Return the evidence used for one candidate triple."""
    return explain_candidate_link_backend(graph_uri, subject, predicate, object_, method)


@mcp.tool()
def export_rdf_patch_tool(predictions: list[dict], threshold: float = 0.8) -> str:
    """Serialize high-scoring predictions as a Turtle patch."""
    return export_rdf_patch(predictions, threshold)


@mcp.tool()
def train_complex_on_profession_graphs(
    output_json: str = "outputs/05_complex_profession_predictions.json",
    output_text: str = "outputs/00_final_demo_output.txt",
    limit: int = 300,
) -> dict:
    """Train the ComplEx example on pseudo-labels from the three profession RDF graphs."""
    return run_complex_profession_demo(output_json, output_text, limit)


if __name__ == "__main__":
    mcp.run()
