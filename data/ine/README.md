# INE indicator catalogue cache

Populated by `scripts/fetch_ine_catalogue.py` (via the `ine-catalogue.yml`
workflow, manual dispatch): `catalogue.xml.gz` (raw, gzipped),
`indicators.csv` (parsed rows), `SUMMARY.md` (counts and themes).

INE's bot protection blocks fetches from GitHub's cloud IPs (403/timeout),
so there is an offline path: download the catalogue from a normal
connection and upload it **to this folder** as **`raw.xml`**:

    https://www.ine.pt/ine/xml_indic.jsp?opc=2&lang=PT   (~21 MB XML)

The next `ine-catalogue.yml` run processes the committed file instead of
fetching, then deletes it — the gzipped copy is the durable cache.
