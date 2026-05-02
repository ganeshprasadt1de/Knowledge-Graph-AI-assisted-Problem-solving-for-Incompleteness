# Task 3 Solution

## Assignment Coverage

| Requirement | Where it is addressed |
| --- | --- |
| Define the problem, input, output, and MCP API | Section 1 |
| Describe training data for the model | Section 2 |
| Identify three methods with input, output, and preprocessing | Section 3 |
| Discuss knowledge graph data, geometry, and multimodal limitations | Section 4 |

## 1. Problem Definition

The selected problem is:

```text
Predicting missing host and penetration links for openings, doors, windows, and service elements in an IFC-derived building knowledge graph.
```

In a real design workflow, an architect may receive a BIM model where the geometry exists, but some semantic links are missing.

The implementation uses three profession-specific IFC files:

```text
ifc files from different professions/Ifc4_Revit_ARC.ifc
ifc files from different professions/Ifc4_Revit_STR.ifc
ifc files from different professions/Ifc4_Revit_MEP.ifc
```

These files are converted into three RDF graphs:

```text
graphs/professions/arc_lbd.ttl
graphs/professions/str_lbd.ttl
graphs/professions/mep_lbd.ttl
```

This matches the multi-discipline coordination problem. The system can compare architectural, structural, and MEP graph data and propose missing cross-discipline links such as:

```text
Architectural wall sameAs Structural wall
MEP duct segment penetrates Structural beam or wall
MEP duct segment requiresOpeningIn Structural element
```

Semantic links are meaning-based relationships. They explain what one object does with another object.

Example:

```text
Window_01 is hosted by Wall_05.
Door_02 fills Opening_02.
FlowTerminal_03 penetrates Wall_07.
Opening_02 voids Wall_05.
```

If these links are missing, the graph may still contain walls, windows, doors, openings, and geometry, but the program cannot reliably answer coordination questions.

Example design question:

```text
Which wall is cut by this opening?
```

Another example:

```text
Does this service element pass through a wall, and does the wall already have a valid opening?
```

This matters in architectural coordination because missing host and penetration links can hide design conflicts. When architectural, structural, and service models are merged, connection data can be lost during export, conversion, or model federation. If the graph is missing a penetration link between a service element and a structural wall, the design team may fail to review the required opening. In a construction workflow, this can lead to late coordination changes, incorrect wall openings, or unsafe modifications to load-bearing elements.

Load-bearing element means a wall, beam, column, or slab that carries structural loads. Cutting such an element without structural review can damage the building system.

The main input used for this task is:

```text
graphs/professions/arc_lbd.ttl
graphs/professions/str_lbd.ttl
graphs/professions/mep_lbd.ttl
```

These RDF graphs were generated from:

```text
Ifc4_Revit_ARC.ifc
Ifc4_Revit_STR.ifc
Ifc4_Revit_MEP.ifc
```

using the IFCtoLBD converter.

Observed graph contents:

```text
Architecture graph:
Triples: 12667
BOT elements: 489
Walls: 47
Doors: 16
Windows: 17
IFC opening elements: 35
Geometry links: 481

Structure graph:
Triples: 108588
BOT elements: 4150
Walls: 9
Beams: 370
Columns: 30
Slabs: 37
Geometry links: 4133

MEP graph:
Triples: 171309
BOT elements: 6955
Duct fittings: 935
Duct segments: 837
Flow terminals: 11
Geometry links: 7081
```

BOT means Building Topology Ontology. It is an ontology for representing buildings, storeys, spaces, and elements.

LBD means Linked Building Data. It uses RDF and ontologies to represent building information as linked facts.

The problem follows the RDF Open World Assumption.

Open World Assumption means:

```text
If a fact is missing from the graph, the fact is not automatically false.
The graph may simply be incomplete.
```

For example, if the graph does not state that `Opening_01` voids `Wall_05`, this does not prove that the opening does not void the wall. It only means the graph does not contain that fact.

### 1.1 Input

The module receives an RDF building graph generated from IFC.

Input format:

```text
Turtle RDF file
```

Example:

```text
graphs/professions/arc_lbd.ttl
graphs/professions/str_lbd.ttl
graphs/professions/mep_lbd.ttl
```

The graphs may contain:

```text
Walls
Doors
Windows
Opening elements
Flow terminals
Beams
Columns
Slabs
Duct segments
Duct fittings
Storeys
Element labels
IFC GlobalIds
Bounding boxes
Geometry links
BOT subelement links
```

The observed graphs contain bounding-box relations such as:

```text
lbd:containsInBoundingBox
```

A bounding box is a simple rectangular 3D box around an object. It supports checks for whether two objects are near each other or overlap.

### 1.2 Output

The output is a ranked list of candidate missing triples.

A triple is one RDF fact:

```text
subject - predicate - object
```

Example candidate outputs:

```text
(Opening_01, voidsElement, Wall_05): 0.91
(Window_01, fillsOpening, Opening_01): 0.86
(FlowTerminal_01, penetrates, Wall_07): 0.78
(FlowTerminal_01, requiresOpeningIn, Wall_07): 0.74
```

The number is a plausibility score.

A plausibility score is a model score that estimates how likely the triple is to be true.

The output should not be treated as a final architectural decision. It is a ranked suggestion list for review by an architect, BIM coordinator, or engineer.

### 1.3 Implemented MCP Server API

An MCP server is implemented in:

```text
scripts/mcp_server.py
```

The API backend is implemented in:

```text
scripts/coordination_core.py
```

Local API test commands are implemented in:

```text
scripts/call_api.py
```

The full API usage guide is:

```text
API_GUIDE.md
```

The MCP server exposes the solution as tools for an agentic AI system.

MCP means Model Context Protocol. In this context, it is a way for an AI agent to call external tools. Agentic AI means an AI system that can call tools and perform several steps instead of only writing text.

Implemented API:

```text
inspect_profession_graphs(arc_graph_uri, str_graph_uri, mep_graph_uri)
```

Purpose:

```text
Read the architecture, structure, and MEP RDF graphs and report available element types, predicates, and geometry support.
```

Input:

```json
{
  "arc_graph_uri": "graphs/professions/arc_lbd.ttl",
  "str_graph_uri": "graphs/professions/str_lbd.ttl",
  "mep_graph_uri": "graphs/professions/mep_lbd.ttl"
}
```

Output:

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

```text
find_cross_discipline_links(arc_graph_uri, str_graph_uri, mep_graph_uri, target_relations)
```

Purpose:

```text
Find element pairs across profession graphs where sameAs, penetration, or opening-required relations may be missing.
```

Input:

```json
{
  "arc_graph_uri": "graphs/professions/arc_lbd.ttl",
  "str_graph_uri": "graphs/professions/str_lbd.ttl",
  "mep_graph_uri": "graphs/professions/mep_lbd.ttl",
  "target_relations": [
    "sameAs",
    "penetrates",
    "requiresOpeningIn"
  ]
}
```

Output:

```json
{
  "candidates": [
    {
      "subject": "https://example.org/professions/mep/ductsegment_a357...",
      "predicate": "penetrates",
      "object": "https://example.org/professions/str/beam_722...",
      "score": 0.654
    }
  ]
}
```

```text
score_candidate_triple(graph_uri, subject, predicate, object)
```

Purpose:

```text
Score one possible missing fact.
```

Input:

```json
{
  "graph_uri": "graphs/professions/mep_lbd.ttl",
  "subject": "FlowTerminal_01",
  "predicate": "penetrates",
  "object": "Wall_07"
}
```

Output:

```json
{
  "score": 0.78,
  "interpretation": "plausible"
}
```

```text
explain_candidate_link(graph_uri, subject, predicate, object)
```

Purpose:

```text
Return the graph and geometry evidence used for a prediction.
```

Output example:

```json
{
  "evidence": [
    "the elements have geometry links",
    "the elements have overlapping or contained bounding boxes",
    "similar element pairs appear as positive examples in training data"
  ]
}
```

```text
export_rdf_patch(predictions, threshold)
```

Purpose:

```text
Export high-scoring predictions as RDF triples.
```

Example output:

```turtle
:Opening_01 :voidsElement :Wall_05 .
:Window_01 :fillsOpening :Opening_01 .
```

The patch should be reviewed before insertion into the project graph.

## 2. Training Data

Embedding methods need training triples. The three profession RDF graphs are used for project checking, while the BIM Spatial Models dataset is used for training examples.

Training data should contain many coordinated building graphs where the correct relations are already known.

Training sources:

```text
Federated IFC models from architecture, structure, and MEP coordination workflows
IFC files converted to RDF through IFCtoLBD or ifcOWL
Clash detection reports from tools such as Solibri or Navisworks
BIM issue tracking records from coordination meetings
Manually validated host, opening, and penetration relations
Graph patches approved by BIM coordinators
```

Federated model means a project model assembled from separate discipline models. For example, the architectural model, structural model, and MEP model are linked but not necessarily stored as one original file.

### 2.1 Dataset Creation Blueprint

The training dataset can be created from complete or manually validated BIM models.

The process is:

```text
1. Collect complete IFC models from coordinated projects.
2. Convert each IFC model into an RDF graph using IFCtoLBD or ifcOWL.
3. Extract correct host, filling, void, and penetration triples.
4. Store these triples as the ground truth.
5. Intentionally remove some of these triples from the graph.
6. Train the model to predict the removed triples.
7. Compare the predicted triples with the original ground-truth triples.
```

Ground truth means the reference answer treated as correct during training or evaluation.

Example complete graph:

```text
(Window_01, isHostedBy, Wall_05)
(Opening_01, voidsElement, Wall_05)
(FlowTerminal_03, penetrates, Wall_07)
```

Corrupted training graph:

```text
(Window_01, isHostedBy, ?)
(Opening_01, voidsElement, ?)
(FlowTerminal_03, penetrates, ?)
```

The model receives the corrupted graph as input and tries to recover the deleted facts. The original complete graph is then used to check whether the model recovered the correct answer.

This setup matches the real problem because the graph can be incomplete while the missing relation may still be true.

### 2.2 Positive And Negative Samples

The training graph should contain positive examples.

Positive examples are facts known to be true:

```text
(Opening_01, voidsElement, Wall_05)
(Window_01, fillsOpening, Opening_01)
(FlowTerminal_03, penetrates, Wall_07)
(FlowTerminal_03, requiresOpeningIn, Wall_07)
```

The training process also needs negative samples.

Negative samples are generated false or unlikely triples:

```text
(Opening_01, voidsElement, Chair_02)
(Window_01, fillsOpening, Slab_03)
(FlowTerminal_03, penetrates, Furniture_04)
```

Negative samples help the model learn what should receive a low score.

For embedding methods, negative samples are usually generated by corrupting one part of a true triple.

Example true triple:

```text
(Window_01, isHostedBy, Wall_05)
```

Example corrupted triples:

```text
(Window_01, isHostedBy, Roof_02)
(Chair_04, isHostedBy, Wall_05)
(Window_01, penetrates, Furniture_08)
```

These examples are not added as real building facts. They are training examples that teach the model what wrong coordination links look like.

### 2.3 Features From The RDF Graph

Training features include:

```text
Element type
Element label
IFC GlobalId
Storey
Bounding-box coordinates
Geometry relation
BOT subelement relation
Object type property
Material or load-bearing property when available
Known host or filling relations
```

In the generated RDF graph, the available evidence includes:

```text
Element classes such as Wall, Door, Window, IfcOpeningElement, FlowTerminal
Labels from rdfs:label
Global IDs from props:globalIdIfcRoot_attribute_simple
Object types from props:objectTypeIfcObject_attribute_simple
Geometry links from omg:hasGeometry
Bounding-box values such as lbd:x-min, lbd:x-max, lbd:y-min, lbd:y-max, lbd:z-min, lbd:z-max
Bounding-box containment links from lbd:containsInBoundingBox
Subelement links from bot:hasSubElement
```

### 2.4 How The Downloaded Dataset Helps

The downloaded BIM Spatial Models dataset helps because it already contains spatial relationship labels.

The important file is:

```text
spatial_relationships_detailed.csv
```

Each row gives two building objects and one spatial relationship.

Example:

```text
name1, name2, relation
Door object, Wall object, Partially Embedded
```

The program does not discover this relation from raw dataset geometry. The dataset already provides the relation label. The program uses that label as training data.

Training label means the answer used to teach the model.

The program simplifies the object names into object types.

Example:

```text
M_Single-Flush:0915 x 2134mm:154820:1 -> Door
Interior Wall:153506 -> Wall
Partially Embedded -> partially_embedded
```

The training triple becomes:

```text
Door partially_embedded Wall
```

This teaches the model that a door can be partially embedded in a wall.

The same idea is used for other rows.

Example:

```text
Window face_overlap Wall
Service_Element partially_embedded Beam
```

The program also creates negative triples by replacing the object type.

Example positive triple:

```text
Window face_overlap Wall
```

Example negative triple:

```text
Window face_overlap Slab
```

This teaches the model that some type relationships are more likely than others.

For the project graphs, geometry is checked directly from RDF bounding boxes. This is different from the training dataset step.

In short:

```text
The dataset teaches type-level spatial patterns.
The project RDF graphs provide the actual geometry overlaps to check.
```

## 3. Existing Methods

The three selected methods are knowledge graph embedding methods:

```text
TransE
RotatE
ComplEx
```

Knowledge graph embedding means converting entities and relations into vectors.

A vector is a list of numbers.

Example:

```text
Wall_05 = [0.12, -0.44, 0.31]
Opening_01 = [0.20, -0.39, 0.28]
voidsElement = [0.08, 0.05, -0.03]
```

The model learns vector patterns that make true triples score higher than false triples.

### 3.1 Shared Preprocessing For Embedding Methods

TransE, RotatE, and ComplEx cannot directly learn from raw Turtle text such as:

```text
inst:window_84de20a0 bot:hasSubElement inst:wall_92f93668
```

The graph must first be converted into numerical training data.

Preprocessing steps:

```text
1. Parse the RDF graph.
2. Collect every unique entity IRI.
3. Collect every unique relation IRI.
4. Assign each entity a unique integer ID.
5. Assign each relation a unique integer ID.
6. Convert every triple into integer form:
   (head_entity_id, relation_id, tail_entity_id)
7. Generate negative samples by replacing the head or tail entity.
8. Split the triples into training, validation, and test sets.
```

Example mapping:

```text
Window_01 -> entity ID 15
Wall_05 -> entity ID 88
isHostedBy -> relation ID 6
```

Example model input:

```text
(15, 6, 88)
```

This means:

```text
(Window_01, isHostedBy, Wall_05)
```

The model output is a score for a candidate triple.

Example:

```text
Input candidate: (Window_01, isHostedBy, Wall_05)
Output score: 0.86
```

The score estimates how plausible the triple is. A high score means the model thinks the relation is likely true. A low score means the model thinks the relation is unlikely.

### 3.2 Method 1: TransE

TransE represents a relation as a translation in vector space.

Translation here means mathematical movement, not physical movement in the building.

TransE tries to learn:

```text
head + relation ~= tail
```

For the candidate triple:

```text
(Opening_01, voidsElement, Wall_05)
```

TransE tries to make:

```text
Opening_01 + voidsElement ~= Wall_05
```

Input:

```text
Training triples from coordinated building knowledge graphs.
```

Output:

```text
Plausibility scores for candidate missing host and penetration triples.
```

Preprocessing:

```text
Convert IFC models to RDF.
Extract entities and relations.
Normalize equivalent labels and classes.
Generate candidate triples.
Generate negative samples.
Split triples into training, validation, and test sets.
```

Alignment with this problem:

```text
Training input: integer triples such as (opening_id, voidsElement_id, wall_id).
Prediction input: a fixed relation query such as (opening_id, voidsElement_id, candidate_wall_id).
Prediction output: one plausibility score for each candidate wall.
Example output triple: (Opening_01, voidsElement, Wall_05) with a high score.
```

Main limitation:

```text
TransE can struggle with many-to-many relations.
```

A many-to-many relation means one object can relate to many objects, and many objects can relate to one object. For example, one wall can contain several windows, and many walls can contain openings.

### 3.3 Method 2: RotatE

RotatE represents relations as rotations in complex vector space.

Complex vector space means the vectors use complex numbers. A complex number has a real part and an imaginary part. The practical idea is that a relation rotates one entity vector toward another.

RotatE can model relation patterns such as inverse relations and composition.

Inverse relation example:

```text
(Opening_01, voidsElement, Wall_05)
(Wall_05, voidedBy, Opening_01)
```

Composition example:

```text
(FlowTerminal_01, intersects, Wall_07)
(Wall_07, isLoadBearing, true)
```

This can support the prediction:

```text
(FlowTerminal_01, requiresOpeningIn, Wall_07)
```

Input:

```text
RDF triples from building graphs, including semantic and geometry-derived relations.
```

Output:

```text
Ranked candidate triples with plausibility scores.
```

Preprocessing:

```text
Convert RDF to indexed entity-relation triples.
Add geometry-derived relations such as overlapsBoundingBox when available.
Generate inverse relation examples if the training setup uses them.
Generate negative samples.
```

Alignment with this problem:

```text
Training input: indexed graph triples, including optional inverse relations.
Prediction input: a candidate triple such as (flow_terminal_id, requiresOpeningIn_id, wall_id).
Prediction output: a ranked list of candidate triples with scores.
The method is suitable when relation direction and inverse patterns matter.
```

Main limitation:

```text
RotatE depends on training examples. Without enough examples, its scores are weak.
```

### 3.4 Method 3: ComplEx

ComplEx uses complex-valued embeddings and can model directional relations.

Directional relation means the order of subject and object matters.

Example:

```text
(FlowTerminal_03, penetrates, Wall_07)
```

is not the same as:

```text
(Wall_07, penetrates, FlowTerminal_03)
```

Input:

```text
Knowledge graph triples from coordinated IFC-derived RDF graphs.
```

Output:

```text
Scores for candidate missing triples.
```

Preprocessing:

```text
Parse RDF triples.
Map IRIs to entity IDs.
Map predicates to relation IDs.
Normalize labels and duplicate concepts.
Create train, validation, and test sets.
Generate negative triples.
```

Alignment with this problem:

```text
Training input: indexed subject-relation-object triples.
Prediction input: a candidate directional triple such as (flow_terminal_id, penetrates_id, wall_id).
Prediction output: a plausibility score for that exact direction.
The method can distinguish directional facts such as penetrates, requiresOpeningIn, fillsOpening, and voidsElement.
```

Main limitation:

```text
ComplEx does not use raw geometry directly. Geometry must first be converted into graph relations or numeric features.
```

## 4. Knowledge Graph Problem Or Multimodal Problem

This is not a purely knowledge graph problem.

It can be represented as knowledge graph completion, but the architectural meaning depends on both semantic data and geometric data.

Semantic data means meaning-based facts.

Example:

```text
Wall_05 rdf:type beo:Wall.
Opening_01 rdf:type ifc:IfcOpeningElement.
Window_01 rdf:type beo:Window.
```

Geometric data means shape, size, position, or spatial relation.

Example:

```text
Wall_05 has bounding box coordinates.
Opening_01 has geometry.
Opening_01 is inside or overlaps the wall area.
```

In the generated graph, geometry is present through:

```text
omg:hasGeometry
fog:asObj_v3.0-obj
lbd:hasBoundingBox
lbd:containsInBoundingBox
lbd:x-min / x-max / y-min / y-max / z-min / z-max
```

### 4.1 Scenario A: Graph Data Only, No Geometry

With graph data only, the graph still contains semantic facts, but the program has no physical position, size, or shape data.

Example:

```text
Wall_05 bot:hasSubElement Window_01.
Window_01 rdf:type beo:Window.
Wall_05 rdf:type beo:Wall.
```

From this, the model may infer:

```text
Window_01 probably fills an opening in Wall_05.
```

However, if geometry is removed, including relations such as `omg:hasGeometry`, `lbd:hasBoundingBox`, and bounding-box coordinates, the model cannot reliably check whether the window physically lies inside the wall.

The model may know the general rule:

```text
Windows are usually hosted by walls.
```

But it cannot know which specific wall hosts which specific window unless the graph already contains enough non-geometric relations, such as `bot:hasSubElement`.

This creates uncertainty.

### 4.2 Scenario B: Geometry Only, No Graph Semantics

With geometry only, the program still sees shapes, bounding boxes, and intersections, but it no longer knows the meaning of the objects.

Example:

```text
An opening bounding box lies inside a wall bounding box.
```

The program may infer:

```text
The opening probably voids the wall.
```

But geometry alone is not enough to understand design meaning. If labels and classes such as `beo:Window`, `beo:Wall`, `ifc:IfcOpeningElement`, and `mep:FlowTerminal` are removed, the program may only see one object intersecting another object.

Example:

```text
Two objects overlap.
```

This may mean:

```text
A valid wall-window connection.
A valid pipe penetration.
A modeling error.
A serious clash.
```

Without semantic types, the program cannot know whether the overlap is expected or problematic.

### 4.3 If Both Modalities Are Available

The best solution uses both graph semantics and geometry.

Example:

```text
The subject is an IfcOpeningElement.
The object is a Wall.
Both have geometry.
The opening bounding box is inside the wall bounding box.
Similar examples in training data are labeled as voidsElement.
```

This gives stronger evidence for:

```text
(Opening_01, voidsElement, Wall_05)
```

Final position:

```text
The problem can be formulated as knowledge graph completion, but it requires multimodal information for reliable architectural use. Graph semantics explain what the objects are. Geometry explains where the objects are and whether they physically interact.
```

In practical terms:

```text
Geometry is needed to detect physical intersections, containment, and possible clashes.
Graph semantics are needed to understand whether the intersecting objects are walls, openings, windows, doors, service elements, or structural elements.
```

## 5. Practical Scope

Geometry rules can create candidate links from the generated RDF graph.

Example rule:

```text
If an IfcOpeningElement has a bounding box contained in a Wall bounding box, propose (Opening, voidsElement, Wall).
```

A machine learning version using TransE, RotatE, or ComplEx requires a larger dataset.

The implementation uses the downloaded BIM Spatial Models dataset for embedding training. The training script is:

```text
scripts/embedding_training.py
```

The dataset contains `spatial_relationships_detailed.csv` files. These files provide positive spatial relationship examples such as:

```text
Partially Embedded
Fully Contained
Face Overlap
```

The preprocessing step converts each row into an element-type triple.

Example:

```text
(Door, partially_embedded, Wall)
(Window, face_overlap, Wall)
(Service_Element, partially_embedded, Beam)
```

Negative triples are generated by replacing the object type inside the same project.

Example:

```text
(Door, partially_embedded, Slab)
```

This gives the embedding method examples of likely and unlikely spatial relationships.

The trained model is then used with the architecture, structure, and MEP RDF graphs. The program first finds geometric overlaps in the RDF graphs, then scores those candidate problems with the trained embedding model.

The report is written to:

```text
outputs/coordination_report.txt
outputs/coordination_report.json
```

The report is a ranked review list, not an automatic construction decision.

The project data supports:

```text
Problem definition
API design
RDF inspection
Candidate generation
Coordination report generation
```

The project data does not support:

```text
Guaranteeing that every predicted problem is correct
Replacing BIM coordinator or structural engineer review
Guaranteeing accuracy on unseen buildings
```
