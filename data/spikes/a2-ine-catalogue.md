# Spike A2: INE catalogue enumerability

Question: can the full INE indicator catalogue be listed programmatically? Raw responses in the `spike-raw` artifact.

## json-series-example

`https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0000611&lang=PT`

- FAILED: HTTP Error 403: Forbidden

## json-metadata-example

`https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp?varcd=0000611&lang=PT`

- FAILED: HTTP Error 403: Forbidden

## xml-catalogue-opc1

`https://www.ine.pt/ine/xml_indic.jsp?opc=1&lang=PT`

- FAILED: HTTP Error 403: Forbidden

## xml-catalogue-opc2

`https://www.ine.pt/ine/xml_indic.jsp?opc=2&lang=PT`

- FAILED: <urlopen error timed out>

## dadosgov-ine-search

`https://dados.gov.pt/api/1/datasets/?q=ine%20indicadores&page_size=5`

- HTTP 200, 26,210 bytes, application/json
- entry-pattern counts: none
- parsed as JSON: 5 top-level items
- sample: `{"data": [{"access_audiences": [], "access_type": "open", "access_type_reason": null, "access_type_reason_category": null, "acronym": null, "archived": null, "authorization_request_url": null, "badges": [], "contact_points": [], "created_at": "2026-02-11T10:19:20.111000+00:00", "`

