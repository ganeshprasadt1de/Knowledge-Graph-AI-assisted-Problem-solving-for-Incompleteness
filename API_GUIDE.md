# API Guide

## 1. Implemented API

The implemented API is in:

```text
scripts/coordination_core.py
```

The MCP server wrapper is in:

```text
scripts/mcp_server.py
```

The local command-line caller is in:

```text
scripts/call_api.py
```

The API works on the generated profession RDF graphs:

```text
graphs/professions/arc_lbd.ttl
graphs/professions/str_lbd.ttl
graphs/professions/mep_lbd.ttl
```

The API demonstrates the coordination-link problem on architecture, structure, and MEP IFC-derived graphs. It supports cross-discipline candidates such as architectural wall to structural wall `sameAs`, MEP element `penetrates` structural element, and MEP element `requiresOpeningIn` structural element.

## 2. Install Dependencies

Install the Python packages:

```powershell
pip install -r requirements.txt
```

The dependencies are:

```text
rdflib
mcp
```

`rdflib` parses the Turtle RDF graph. `mcp` provides the Model Context Protocol server runtime.

## 3. MCP Server

The MCP server uses stdio transport. In stdio transport, the client starts the server process and communicates with it through standard input and output. This is different from a REST API, so there is no browser URL or `curl` endpoint.

Start command used by an MCP client:

```powershell
python .\scripts\mcp_server.py
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "building-coordination-kg": {
      "command": "python",
      "args": [
        "C:\\Users\\ganes\\Desktop\\Ubung - UniStuttgart\\Ubung - UniStuttgart\\LAB - Knowledge representations for Buildings\\Task - 3 - Submission\\scripts\\mcp_server.py"
      ],
      "cwd": "C:\\Users\\ganes\\Desktop\\Ubung - UniStuttgart\\Ubung - UniStuttgart\\LAB - Knowledge representations for Buildings\\Task - 3 - Submission"
    }
  }
}
```

Use the absolute folder path that matches the local machine when copying this configuration into an MCP client.

## 4. MCP Tools

### 4.1 `inspect_lbd_graph`

Purpose:

```text
Read the RDF graph and return basic graph statistics.
```

Arguments:

```json
{
  "graph_uri": "graphs/professions/arc_lbd.ttl"
}
```

Example output:

```json
{
  "triples": 2673,
  "subjects": 392,
  "predicates": 38,
  "objects": 1561,
  "bot_elements": 130,
  "walls": 27,
  "doors": 5,
  "windows": 15,
  "opening_elements": 20,
  "flow_terminals": 3,
  "furniture": 49,
  "storeys": 2,
  "geometry_links": 129,
  "bounding_box_links": 303,
  "bot_subelement_links": 21
}
```

### 4.2 `inspect_profession_graphs`

Purpose:

```text
Read the architecture, structure, and MEP RDF graphs and return graph statistics for each discipline.
```

Arguments:

```json
{
  "arc_graph_uri": "graphs/professions/arc_lbd.ttl",
  "str_graph_uri": "graphs/professions/str_lbd.ttl",
  "mep_graph_uri": "graphs/professions/mep_lbd.ttl"
}
```

Example output:

```json
{
  "architecture": {
    "triples": 12667,
    "walls": 47,
    "doors": 16,
    "windows": 17,
    "opening_elements": 35
  },
  "structure": {
    "triples": 108588,
    "walls": 9,
    "geometry_links": 4133
  },
  "mep": {
    "triples": 171309,
    "flow_terminals": 11,
    "geometry_links": 7081
  }
}
```

### 4.3 `find_cross_discipline_links`

Purpose:

```text
Find candidate missing coordination triples across architecture, structure, and MEP graphs.
```

Arguments:

```json
{
  "arc_graph_uri": "graphs/professions/arc_lbd.ttl",
  "str_graph_uri": "graphs/professions/str_lbd.ttl",
  "mep_graph_uri": "graphs/professions/mep_lbd.ttl",
  "target_relations": ["sameAs", "penetrates", "requiresOpeningIn"],
  "method": "rule",
  "limit": 5
}
```

Example output:

```json
{
  "method": "rule",
  "status": "ok",
  "candidate_count": 260,
  "candidates": [
    {
      "subject": "https://example.org/professions/mep/ductfitting_a67143fa-0884-41a0-b6e9-3c9e8fe3aba4",
      "predicate": "penetrates",
      "object": "https://example.org/professions/str/beam_bbf8378f-8492-45a2-9f13-25c7dda76551",
      "score": 0.666,
      "method": "rule"
    }
  ]
}
```

### 4.4 `find_missing_coordination_links`

Purpose:

```text
Find candidate missing coordination triples.
```

Arguments:

```json
{
  "graph_uri": "graphs/professions/arc_lbd.ttl",
  "target_relations": ["isHostedBy", "voidsElement", "penetrates", "requiresOpeningIn"],
  "method": "rule",
  "limit": 5
}
```

Example output:

```json
{
  "method": "rule",
  "status": "ok",
  "candidate_count": 22,
  "candidates": [
    {
      "subject": "https://example.org/professions/arc/window_example",
      "predicate": "isHostedBy",
      "object": "https://example.org/professions/arc/wall_example",
      "score": 0.86,
      "method": "rule",
      "evidence": [
        "wall has bot:hasSubElement relation to a door or window",
        "object is typed as beo:Wall"
      ]
    }
  ]
}
```

### 4.5 `score_candidate_triple`

Purpose:

```text
Score one candidate triple.
```

Arguments:

```json
{
  "graph_uri": "graphs/professions/arc_lbd.ttl",
  "subject": "https://example.org/professions/arc/window_example",
  "predicate": "isHostedBy",
  "object_": "https://example.org/professions/arc/wall_example",
  "method": "rule"
}
```

Example output:

```json
{
  "method": "rule",
  "status": "ok",
  "score": 0.86,
  "evidence": [
    "wall has bot:hasSubElement relation to a door or window",
    "object is typed as beo:Wall"
  ]
}
```

### 4.6 `explain_candidate_link`

Purpose:

```text
Return the evidence used to score one candidate triple.
```

Arguments are the same as `score_candidate_triple`.

### 4.7 `export_rdf_patch_tool`

Purpose:

```text
Serialize high-scoring predictions as Turtle RDF triples.
```

Arguments:

```json
{
  "predictions": [
    {
      "subject": "https://example.org/professions/arc/window_example",
      "predicate": "isHostedBy",
      "object": "https://example.org/professions/arc/wall_example",
      "score": 0.86
    }
  ],
  "threshold": 0.8
}
```

Example output:

```turtle
@prefix coord: <https://example.org/coordination#> .

<https://example.org/professions/arc/window_example> <https://example.org/coordination#isHostedBy> <https://example.org/professions/arc/wall_example> .
```

## 5. Local API Calls Without An MCP Client

The local caller uses the same backend functions as the MCP tools. It is useful for testing.

Inspect the graph:

```powershell
python .\scripts\call_api.py inspect-professions .\graphs\professions\arc_lbd.ttl .\graphs\professions\str_lbd.ttl .\graphs\professions\mep_lbd.ttl
```

Find cross-discipline candidate links:

```powershell
python .\scripts\call_api.py find-cross-links .\graphs\professions\arc_lbd.ttl .\graphs\professions\str_lbd.ttl .\graphs\professions\mep_lbd.ttl --limit 5
```

Test the TransE method hook:

```powershell
python .\scripts\call_api.py find-cross-links .\graphs\professions\arc_lbd.ttl .\graphs\professions\str_lbd.ttl .\graphs\professions\mep_lbd.ttl --method TransE --limit 5
```

Expected output:

```json
{
  "method": "TransE",
  "status": "not_trained",
  "message": "TransE requires trained entity and relation embeddings. The current project has a small set of profession RDF graphs, which is enough for candidate generation but not enough for a defensible trained embedding model.",
  "candidates": []
}
```

Run the synthetic ComplEx training demo:

```powershell
python .\scripts\synthetic_complex_demo.py --output .\outputs\05_synthetic_complex_predictions.json
```

Expected top predictions:

```text
(Duct_22, penetrates, Struct_Wall_57): 0.985
(Duct_22, requiresOpeningIn, Struct_Wall_57): 0.984
(Arch_Wall_101, sameAs, Struct_Wall_57): 0.963
```

This output is trained on artificial triples created inside `scripts/synthetic_complex_demo.py`. It demonstrates how ComplEx scoring works, but it is not trained on the real IFC-derived RDF graphs.

Create abstract presentation outputs:

```powershell
python .\scripts\create_final_outputs.py
```

This writes:

```text
outputs/00_final_demo_output.txt
outputs/01_graph_summary_abstract.json
outputs/02_penetration_candidates_abstract.json
outputs/03_sameas_candidates_abstract.json
```

The abstract JSON files use readable element names instead of raw RDF IRIs.

## 6. Use Of TransE, RotatE, And ComplEx

TransE, RotatE, and ComplEx are included as method options in the API:

```text
method = "TransE"
method = "RotatE"
method = "ComplEx"
```

They are not used to produce final scores in this project because no trained embedding model is available.

This is a data limitation, not an API limitation. These methods require:

```text
many coordinated RDF building graphs
known positive triples
generated negative triples
training, validation, and test splits
trained entity embeddings
trained relation embeddings
```

The current project has three generated profession RDF graphs. These graphs are enough to demonstrate:

```text
RDF input
candidate generation
MCP tool design
rule-based scoring
method selection
```

It is not enough to honestly train and evaluate TransE, RotatE, or ComplEx.

The file `scripts/synthetic_complex_demo.py` provides a separate artificial-data demonstration for ComplEx. It creates small example triples, trains embeddings with negative sampling, and writes ranked predictions to `outputs/05_synthetic_complex_predictions.json`.

## 7. Current Scoring Method

The implemented scoring method is rule-based.

Example rule:

```text
If a wall has a bot:hasSubElement relation to a door or window, propose:
(door_or_window, isHostedBy, wall)
```

Example rule:

```text
If a service element is spatially related to a wall through lbd:containsInBoundingBox, propose:
(service_element, penetrates, wall)
```

These rules are used only to demonstrate the API and the input-output shape of the solution. A trained embedding method would replace or complement the rule scorer when a suitable dataset is available.
