# Building Graph Coordination Link Prediction

## 1. Purpose

The program converts architecture, structure, and MEP IFC models into RDF graphs and searches for missing coordination links between building elements.

The main problem is data incompleteness. A duct may pass through a beam, or an architectural wall may correspond to a structural wall, but the graph may not explicitly contain that relationship.

IFC means Industry Foundation Classes. It is a standard BIM data model for building objects, properties, and relationships.

RDF means Resource Description Framework. It stores information as triples:

```text
subject - predicate - object
```

Example:

```text
Door_01 bot:hasSubElement Opening_01
```

## 2. Project Structure

Input files:

```text
ifc files from different professions/Ifc4_Revit_ARC.ifc
ifc files from different professions/Ifc4_Revit_STR.ifc
ifc files from different professions/Ifc4_Revit_MEP.ifc
jdk-21.0.10+7/
tools/IFCtoLBD-master/
```

Generated files:

```text
graphs/professions/arc_lbd.ttl
graphs/professions/str_lbd.ttl
graphs/professions/mep_lbd.ttl
```

Documentation:

```text
TASK3_SOLUTION.md
API_GUIDE.md
README.md
```

Utility script:

```text
scripts/analyze_lbd_graph.py
scripts/call_api.py
scripts/create_final_outputs.py
scripts/mcp_server.py
scripts/complex_profession_demo.py
```

## 3. System Requirements

The conversion was run on Windows with PowerShell.

The local OpenJDK runtime is used when Java is not available on the system PATH. Maven is not required because IFCtoLBD already includes the needed Java libraries.

Python is needed for the API scripts, MCP server, graph analysis, and ComplEx profession-graph example.

Install the Python dependency:

```powershell
pip install -r requirements.txt
```

## 4. Generate The RDF Graphs

Create the graph output directory:

```powershell
New-Item -ItemType Directory -Force -Path graphs\professions
```

Convert the architecture IFC file:

```powershell
.\jdk-21.0.10+7\bin\java.exe -Xmx6g -cp ".\tools\IFCtoLBD-master\IFCtoLBD_NodeJS\java_libraries\*" org.linkedbuildingdata.ifc2lbd.IFCtoLBDConverter_CLI ".\ifc files from different professions\Ifc4_Revit_ARC.ifc" -t ".\graphs\professions\arc_lbd.ttl" -u "https://example.org/professions/arc/" -be=true -p=true --hasUnits=true --hasGeometry=true
```

Convert the structural IFC file:

```powershell
.\jdk-21.0.10+7\bin\java.exe -Xmx6g -cp ".\tools\IFCtoLBD-master\IFCtoLBD_NodeJS\java_libraries\*" org.linkedbuildingdata.ifc2lbd.IFCtoLBDConverter_CLI ".\ifc files from different professions\Ifc4_Revit_STR.ifc" -t ".\graphs\professions\str_lbd.ttl" -u "https://example.org/professions/str/" -be=true -p=true --hasUnits=true --hasGeometry=true
```

Convert the MEP IFC file:

```powershell
.\jdk-21.0.10+7\bin\java.exe -Xmx6g -cp ".\tools\IFCtoLBD-master\IFCtoLBD_NodeJS\java_libraries\*" org.linkedbuildingdata.ifc2lbd.IFCtoLBDConverter_CLI ".\ifc files from different professions\Ifc4_Revit_MEP.ifc" -t ".\graphs\professions\mep_lbd.ttl" -u "https://example.org/professions/mep/" -be=true -p=true --hasUnits=true --hasGeometry=true
```

The commands write:

```text
graphs/professions/arc_lbd.ttl
graphs/professions/str_lbd.ttl
graphs/professions/mep_lbd.ttl
```

The conversion used IFCtoLBD options for building elements, properties, units, and geometry. The bundled CLI did not accept `--hasWKT` or `--hasPerformanceBoost`, so those options are not part of the documented command.

## 5. Inspect The RDF Graphs

Inspect all three profession graphs through the API:

```powershell
python .\scripts\call_api.py inspect-professions .\graphs\professions\arc_lbd.ttl .\graphs\professions\str_lbd.ttl .\graphs\professions\mep_lbd.ttl
```

Observed graph summaries:

```text
Architecture: 12667 triples, 47 walls, 16 doors, 17 windows, 35 opening elements
Structure: 108588 triples, 4150 BOT elements, 9 walls, 4133 geometry links
MEP: 171309 triples, 6955 BOT elements, 11 flow terminals, 7081 geometry links
```

These numbers come from the generated RDF graphs, not from the original IFC files directly.

Generate abstract presentation outputs:

```powershell
python .\scripts\create_final_outputs.py
```

This command writes abstract result files under `outputs/`. Raw RDF identifiers are replaced with readable names such as `MEP_DuctFitting_01` and `Structural_Beam_01`.

## 6. API And MCP Server

The implemented API and MCP server are documented in:

```text
API_GUIDE.md
```

Start command for an MCP client:

```powershell
python .\scripts\mcp_server.py
```

The server uses MCP stdio transport, so it is started by an MCP client rather than opened in a browser.

Test the same backend locally:

```powershell
python .\scripts\call_api.py find-cross-links .\graphs\professions\arc_lbd.ttl .\graphs\professions\str_lbd.ttl .\graphs\professions\mep_lbd.ttl --limit 5
```

Run the ComplEx profession-graph example:

```powershell
python .\scripts\call_api.py complex-profession-demo --output-json .\outputs\05_complex_profession_predictions.json --output-text .\outputs\00_final_demo_output.txt
```

This command creates pseudo-labels from the three RDF graphs, trains a small ComplEx-style model on those pseudo-labels, and writes the final text output.

Final presentation output:

```text
outputs/00_final_demo_output.txt
```

## 7. Excluded Or Local-Only Files

The following paths are large or generated and should normally stay out of version control:

```text
tools/IFCtoLBD-master/
jdk-21.0.10+7/
graphs/
outputs/
*.zip
*.ifc
```

The RDF files can be regenerated from the IFC files and converter commands above. If the submission requires generated RDF, include the files under `graphs/professions/` explicitly.
