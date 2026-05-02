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

The API handles architecture, structure, and MEP IFC-derived graphs. It supports cross-discipline candidates such as architectural wall to structural wall `sameAs`, MEP element `penetrates` structural element, and MEP element `requiresOpeningIn` structural element.

## 2. Install Dependencies

Install the Python packages:

```powershell
pip install -r requirements.txt
```

The dependencies are:

```text
rdflib
mcp
numpy
```

`rdflib` parses the Turtle RDF graph. `mcp` provides the Model Context Protocol server runtime.
`numpy` is used by the embedding training script.

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

Set the folder path to the local project path when copying this configuration into an MCP client.

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

The long `subject` and `object` values are RDF identifiers. An RDF identifier is a unique name for one object in the graph.

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

### 4.8 `train_embedding_from_bim_spatial_data`

Purpose:

```text
Train TransE, RotatE, or ComplEx from public BIM spatial relationship CSV files.
```

Arguments:

```json
{
  "dataset_dir": "datasets/BIM Spatial Models for Construction Dependency Inf",
  "method": "ComplEx",
  "output_model": "models/bim_spatial_complex_model.json"
}
```

Example output:

```json
{
  "method": "ComplEx",
  "positive_training_triples": 8565,
  "negative_training_triples": 3925,
  "entity_count": 24,
  "relation_count": 3
}
```

Positive triples come from `spatial_relationships_detailed.csv`. Negative triples are generated by replacing the object type inside the same project.

### 4.9 `create_coordination_report_tool`

Purpose:

```text
Read the architecture, structure, and MEP RDF graphs, find overlaps, score them with the trained embedding model, and write a report.
```

Arguments:

```json
{
  "arc_graph_uri": "graphs/professions/arc_lbd.ttl",
  "str_graph_uri": "graphs/professions/str_lbd.ttl",
  "mep_graph_uri": "graphs/professions/mep_lbd.ttl",
  "model_path": "models/bim_spatial_complex_model.json",
  "output_text": "outputs/coordination_report.txt",
  "output_json": "outputs/coordination_report.json",
  "limit": 12
}
```

The report contains these main fields:

```text
score
risk_level
geometry_score
embedding_score
dataset_support_level
dataset_support_count
```

`geometry_score` comes from the three project RDF graphs. It measures how strongly two bounding boxes overlap.

`embedding_score` comes from the trained TransE, RotatE, or ComplEx model. It measures whether the type pattern is common in the training dataset.

`dataset_support_level` explains how much training evidence exists for the type pattern.

```text
direct = the same type pattern exists in the training dataset
backoff = a related but more general type pattern exists
none = no matching type pattern was found
```

## 5. Local API Calls Without An MCP Client

The local caller uses the same backend functions as the MCP tools.

Inspect the graph:

```powershell
python .\scripts\call_api.py inspect-professions .\graphs\professions\arc_lbd.ttl .\graphs\professions\str_lbd.ttl .\graphs\professions\mep_lbd.ttl
```

Find cross-discipline candidate links:

```powershell
python .\scripts\call_api.py find-cross-links .\graphs\professions\arc_lbd.ttl .\graphs\professions\str_lbd.ttl .\graphs\professions\mep_lbd.ttl --limit 5
```

Train the embedding model:

```powershell
python .\scripts\call_api.py train-embedding --dataset ".\datasets\BIM Spatial Models for Construction Dependency Inf" --method ComplEx --output-model ".\models\bim_spatial_complex_model.json"
```

Create the coordination report:

```powershell
python .\scripts\call_api.py coordination-report .\graphs\professions\arc_lbd.ttl .\graphs\professions\str_lbd.ttl .\graphs\professions\mep_lbd.ttl --model .\models\bim_spatial_complex_model.json --output-text .\outputs\coordination_report.txt --output-json .\outputs\coordination_report.json
```

This writes:

```text
outputs/coordination_report.txt
outputs/coordination_report.json
```

## 6. Use Of TransE, RotatE, And ComplEx

TransE, RotatE, and ComplEx are available in the training API:

```text
--method TransE
--method RotatE
--method ComplEx
```

The training script uses public BIM spatial relationship data. The dataset contains these relation labels:

```text
partially_embedded
fully_contained
face_overlap
```

The model is trained on element-type triples rather than raw element IDs. This is needed because the public dataset and the project RDF graphs contain different building elements.

The report score combines three parts:

```text
geometry score from the three RDF graphs
embedding score from the trained public dataset model
dataset support from the training triples
```

## 7. Scoring Method

The report first uses geometry rules to create candidate links.

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

The trained embedding model then scores the candidate type pattern. The final score combines the geometry score, embedding score, and dataset support.
