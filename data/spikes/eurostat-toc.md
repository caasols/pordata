# Spike: Eurostat's catalogue — shape, size and identifiers

Roadmap 2's open half. **Measured before specifying anything**, because spike A5's one-to-many finding is a fact about INE's database and not a law of statistics offices. Candidates, not addresses: every outcome below is recorded, misses included, so a 404 reads as a wrong guess rather than as "not enumerable".

## ok `toc-txt`

- `https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt`
- status 200, 1926 KB, `text/plain;charset=UTF-8`
- looks like **tsv**, 12238 lines
- **8498 distinct dataset-code-shaped tokens**

```
"title"	"code"	"type"	"last update of data"	"last table structure change"	"data start"	"data end"	"values"
"Database by themes"	"data"	"folder"	" "	" "	" "	" "	
"    General and regional statistics"	"general"	"folder"	" "	" "	" "	" "	
"        European and national indicators for short-term analysis"	"euroind"	"folder"	" "	" "	" "	" "	
"            Balance of payments"	"ei_bp"	"folder"	" "	" "	" "	" "	
"                Current account - quarterly data"	"ei_bpm6ca_q"	"table"	"19.08.2026"	"19.08.2026"	"1991-Q1"	"2026-Q2"	311689
"                Financial account - quarterly data"	"ei_bpm6fa_q"	"table"	"19.08.2026"	"19.08.2026"	"1991-Q1"	"2026-Q2"	55400
"                Current account - monthly data"	"ei_bpm6ca_m"	"table"	"19.08.2026"	"19.08.2026"	"1991-01"	"2026-06"	258947
"                Financial account - monthly data"	"ei_bpm6fa_m"	"table"	"19.08.2026"	"19.08.2026"	"1991-01"	"2026-06"	88938
"                International investment position - quarterly data"	"ei_bpm6iip_q"	"table"	"08.07.2026"	"03.07.2026"	"1992-Q4"	"2026-Q1"	69520
"            Business and consumer surveys"	"ei_bcs"	"folder"	" "	" "	" "	" "	
"                Business and consumer survey - composite indicators"	"ei_bcs_mi"	"folder"	" "	" "	" "	" "	
```

## ok `toc-xml`

- `https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/xml`
- status 200, 22580 KB, `application/xml;charset=UTF-8`
- looks like **xml**, 252458 lines
- **9055 distinct dataset-code-shaped tokens**

```
<?xml version="1.0" encoding="UTF-8"?>
<nt:tree xmlns:nt="urn:eu.europa.ec.eurostat.navtree" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:eu.europa.ec.eurostat.navtree https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/TableOfContent.xsd" creationDate="20260824T2100">
  <nt:branch>
    <nt:title language="en">Database by themes</nt:title>
    <nt:title language="fr">Base de données par thèmes</nt:title>
    <nt:title language="de">Datenbank nach Themen</nt:title>
    <nt:code>data</nt:code>
    <nt:children>
      <nt:branch>
        <nt:title language="en">General and regional statistics</nt:title>
        <nt:title language="fr">Statistiques générales et régionales</nt:title>
        <nt:title language="de">Allgemeine und Regionalstatistiken</nt:title>
```

## ok `sdmx-dataflow`

- `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT/all/latest`
- status 200, 36340 KB, `application/vnd.sdmx.structure+xml;version=2.1`
- looks like **xml**, 2 lines
- **8519 distinct dataset-code-shaped tokens**

```
<?xml version="1.0" encoding="UTF-8"?>
<m:Structure xmlns:m="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message" xmlns:s="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure" xmlns:c="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common"><m:Header><m:ID>DF1787605215</m:ID><m:Test>false</m:Test><m:Prepared>2026-08-24T23:00:15.029+02:00</m:Prepared><m:Sender id="ESTAT"/></m:Header><m:Structures><s:Dataflows><s:Dataflow id="LFSQ_EPGAN21" urn="urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=ESTAT:LFSQ_EPGAN21(1.0)" agencyID="ESTAT" version="1.0" isFinal="false"><c:Annotations><c:Annotation><c:AnnotationTitle>DATASET</c:AnnotationTitle><c:AnnotationType>DISSEMINATION_OBJECT_TYPE</c:AnnotationType></c:Annotation><c:Annotation><c:AnnotationTitle>131337</c:AnnotationTitle><c:AnnotationType>OBS_COUNT</c:AnnotationType></c:Annotation><c:Annotation><c:AnnotationTitle>2026-Q1</c:AnnotationTitle><c:AnnotationType>OBS_PERIOD_OVERALL_OLDEST</c:AnnotationType></c:Annotation><c:Annotation><c:AnnotationTitle>2026-Q1</c:AnnotationTitle><c:AnnotationType>OBS_PERIOD_OVERALL_LATEST</c:AnnotationType></c:Annotation><c:Annotation><c:AnnotationTitle>2026-06-12T08:02:48+0200</c:AnnotationTitle><c:AnnotationType>CREATED</c:AnnotationType></c:Annotation><c:Annotation><c:AnnotationTitle>2026-06-12T11:00:00+0200</c:AnnotationTitle><c:AnnotationType>UPDATE_STRUCTURE</c:AnnotationType></c:Annotation><c:Annotation><c:AnnotationTitle>2026-06-12T11:00:00+0200</c:AnnotationTitle><c:Annotat
```

## ok `files-inventory`

- `https://ec.europa.eu/eurostat/api/dissemination/files/inventory?type=data`
- status 200, 4420 KB, `application/octet-stream`
- looks like **tsv**, 8153 lines
- **7412 distinct dataset-code-shaped tokens**

```
Code	Type	Source dataset	Last data change	Last structural change	Data download url (tsv)	Data download url (csv)	Data download url (sdmx)	Data structure download url	Open in Data Browser url
AACT_ALI01	DATASET	-	2026-05-13T11:00:00+0200	2026-03-24T11:00:00+0100	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/AACT_ALI01/?format=TSV	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/AACT_ALI01/?format=SDMX-CSV	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/AACT_ALI01/?format=sdmx_2.1_generic	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT/AACT_ALI01/?references=descendants&format=sdmx_2.1_generic	https://ec.europa.eu/eurostat/databrowser/product/view/AACT_ALI01
AACT_ALI01_R	DATASET	-	2026-03-24T11:00:00+0100	2026-03-24T11:00:00+0100	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/AACT_ALI01_R/?format=TSV	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/AACT_ALI01_R/?format=SDMX-CSV	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/AACT_ALI01_R/?format=sdmx_2.1_generic	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT/AACT_ALI01_R/?references=descendants&format=sdmx_2.1_generic	https://ec.europa.eu/eurostat/databrowser/product/view/AACT_ALI01_R
AACT_ALI02	DATASET	-	2026-05-13T11:00:00+0200	2026-03-24T11:00:00+0100	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/AACT_ALI02/?format=TSV	https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/da
```

## What this has to settle before the crosswalk is written

1. Enumerable without a key — yes/no.
2. **What the unit is.** INE's is a series, which is what made the relation one-to-many. If Eurostat's unit is a *dataset* with dimensions, one PORDATA indicator may map to one dataset plus a dimension filter — a different shape needing a different schema.
3. Catalogue size, so item 16's European half has a denominator.
4. The identifier a fetch URL needs.
