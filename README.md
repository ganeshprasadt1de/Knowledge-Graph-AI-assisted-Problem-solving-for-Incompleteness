# Task 3 RDF Graph Preparation

## 1. Purpose

This folder contains the working files for Task 3. The task uses architecture, structure, and MEP IFC files as building input, converts them to RDF graphs with IFCtoLBD, and uses the generated graphs as the basis for the written assignment and demo.

IFC means Industry Foundation Classes. It is a standard BIM data model for building objects, properties, and relationships.

RDF means Resource Description Framework. It stores information as triples:

```text
subject - predicate - object
```

Example:

```text
Door_01 bot:hasSubElement Opening_01
```

## 2. Files

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

Documentation files:

```text
TASK3_SOLUTION.md
API_GUIDE.md
README.md
```

Utility script:

```text
scripts/analyze_lbd_graph.py
```

## 3. System Requirements

The conversion was run on Windows with PowerShell.

The folder includes a local OpenJDK archive because Java was not available on the system PATH. Maven was not required because the IFCtoLBD ZIP includes the needed Java libraries.

Python is needed only for the graph analysis script.

Install the Python dependency:

```powershell
pip install -r requirements.txt
```

## 4. Generate The RDF Graphs

Create the graph output folder:

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

## 7. Excluded Or Local-Only Files

The following files and folders are large or generated and should normally stay out of version control:

```text
tools/IFCtoLBD-master/
jdk-21.0.10+7/
graphs/
outputs/
*.zip
*.ifc
```

The RDF files can be regenerated from the IFC files and converter commands above. If the submission requires generated RDF, include the files under `graphs/professions/` explicitly.
