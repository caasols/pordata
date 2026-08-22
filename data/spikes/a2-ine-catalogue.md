# Spike A2: INE catalogue enumerability

Question: can the full INE indicator catalogue be listed programmatically? Raw responses in the `spike-raw` artifact.

## docs-page

`https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_api`

- FAILED: HTTP Error 403: Forbidden

## json-series-example

`https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0000611&lang=PT`

- HTTP 200, 1,616,052 bytes, application/json;charset=UTF-8
- entry-pattern counts: `"IndicadorCod"`=1
- parsed as JSON: 1 top-level items
- sample: `[ { "IndicadorCod" : "0000611", "IndicadorDsg" : "População residente (N.º) por Local de residência (NUTS - 2002), Sexo e Grupo etário (Por ciclos de vida); Anual - INE, Estimativas anuais da população residente", "MetaInfUrl" : "https://www.ine.pt/bddXplorer/htdocs/minfo.j`

## json-metadata-example

`https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp?varcd=0000611&lang=PT`

- HTTP 200, 88,431 bytes, application/json;charset=UTF-8
- entry-pattern counts: `"IndicadorCod"`=1
- parsed as JSON: 1 top-level items
- sample: `[ { "IndicadorCod" : "0000611", "IndicadorNome" : "População residente (N.º) por Local de residência (NUTS - 2002), Sexo e Grupo etário (Por ciclos de vida); Anual - INE, Estimativas anuais da população residente", "Periodic" : "Anual", "PrimeiroPeriodo" : "1991", "Ulti`

## xml-catalogue-opc1

`https://www.ine.pt/ine/xml_indic.jsp?opc=1&lang=PT`

- HTTP 200, 6,641 bytes, text/xml;charset=UTF-8
- entry-pattern counts: none
- sample: ` <pre>java.lang.NullPointerException at netgest.bo.ql.QLParser.getObjectDef(QLParser.java:465) at netgest.bo.runtime.boObjectList.<init>(boObjectList.java:233) at netgest.bo.runtime.boObjectList.getObjectList(boObjectList.java:146) at netgest.bo.runtime.boObj`

## xml-catalogue-opc2

`https://www.ine.pt/ine/xml_indic.jsp?opc=2&lang=PT`

- HTTP 200, 21,365,584 bytes, text/xml;charset=UTF-8
- entry-pattern counts: none
- sample: ` <catalog> <extraction_date><![CDATA[Saturday, 22 August 2026, 10:02:02.586 AM]]></extraction_date> <language>PT</language> <indicator id="0000764"> <theme><![CDATA[Transportes e comunicações]]></theme> <subtheme>`

## dadosgov-ine-search

`https://dados.gov.pt/api/1/datasets/?q=ine%20indicadores&page_size=5`

- HTTP 200, 26,210 bytes, application/json
- entry-pattern counts: none
- parsed as JSON: 5 top-level items
- sample: `{"data": [{"access_audiences": [], "access_type": "open", "access_type_reason": null, "access_type_reason_category": null, "acronym": null, "archived": null, "authorization_request_url": null, "badges": [], "contact_points": [], "created_at": "2026-02-11T10:19:20.111000+00:00", "`

