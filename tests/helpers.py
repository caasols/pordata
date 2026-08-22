"""Shared test scaffolding: import the scripts as the `scripts` package
(the import path mutmut instruments) and build a temporary repo layout to
chdir into, since the scripts resolve their data paths relative to the
repo root."""

import importlib
import json
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_script(name: str):
    return importlib.import_module(f"scripts.{name}")


PT = "https://www.pordata.pt"

SAMPLE_URLS = [
    f"{PT}/",
    f"{PT}/portugal/taxa+de+natalidade-99",
    f"{PT}/municipios/medicos+por+habitante-200",
    f"{PT}/municipios/quadro+resumo/abrantes-828209",
    f"{PT}/europa/indice+de+gini-300",
    f"{PT}/tema/portugal/populacao-1",
    f"{PT}/en/portugal/birth+rate-99",
    f"{PT}/en/municipalities/doctors+per+inhabitant-200",
    f"{PT}/en/municipalities/summary+table/abrantes-828209",
    f"{PT}/en/europe/gini+index-300",
    f"{PT}/glossario",
]


class RepoCase(unittest.TestCase):
    """chdir into a throwaway repo layout with sitemap + catalogue files."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)
        pathlib.Path("data/catalogue").mkdir(parents=True)
        pathlib.Path("data/sitemap-urls.txt").write_text(
            "\n".join(SAMPLE_URLS) + "\n", encoding="utf-8")
        pathlib.Path("data/sitemap-lastmod.tsv").write_text(
            "", encoding="utf-8")
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def write_records(self, records: list[dict]):
        pathlib.Path("data/catalogue/pages.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n"
                    for r in records), encoding="utf-8")


def record(url_path: str, rid: int, area: str, name: str, **extra) -> dict:
    rec = {
        "url": f"{PT}/{url_path}",
        "id": rid, "area": area, "slug": url_path.split("/", 1)[-1],
        "name": name, "title": f"{name} | Pordata", "description": f"Sobre {name}",
        "fontes": "INE, PORDATA", "ultima_atualizacao": "2026-06-01",
        "json_ld": {"@type": "WebSite"}, "marker_windows": {},
        "http_status": 200, "bytes": 1000, "harvested_at": "2026-08-22",
    }
    rec.update(extra)
    return rec
