"""Spike A6's parser burned two dispatches before it worked, both times
because the fixture was cleaner than a real page. These tests exist so
the third version stays fixed: every case here is one that shipped
broken."""

import unittest

from helpers import load_script

inv = load_script("spike_page_inventory")

# A page with the hazards the first two fixtures lacked: a <head> full of
# void elements, void elements in the body, an unclosed tag, an attribute
# containing '>', and script text that must never be mistaken for content.
PAGE = """<!DOCTYPE html><html lang="pt"><head>
<meta charset="utf-8"><link rel="icon" href="/x.ico">
<meta name="description" content="a > b"><title>Ignorar</title>
<script>var q = "Pergunta falsa?";</script></head>
<body class="Body"><div class="Wrap"><div class="Row">
<h1 class="title">Diplomados nos cursos</h1><img src="a.png"><br>
<div class="lead"><span class="question">Quantos diplomados ha?</span></div>
<p class="unclosed">Paragrafo sem fecho
<div class="meta"><span class="label">Ultima actualizacao:</span></div>
<table><tr><th>Ano</th><td>1 234 567</td></tr></table>
</div></div></body></html>"""


class LeafTextTest(unittest.TestCase):
    def setUp(self):
        self.parser = inv.LeafText()
        self.parser.feed(PAGE)
        self.groups = dict(self.parser.groups)

    def test_void_tags_in_head_do_not_swallow_the_body(self):
        # the exact bug: <meta>/<link> incremented a skip counter that
        # nothing decremented, so the whole body was skipped and the
        # report claimed 0 groups on a 169 KB page
        self.assertEqual(self.parser.skip_depth, 0)
        self.assertIn("h1.title", self.groups)

    def test_text_is_labelled_by_its_enclosing_tag_and_class(self):
        self.assertEqual(self.groups["span.question"], ["Quantos diplomados ha?"])
        self.assertEqual(self.groups["h1.title"], ["Diplomados nos cursos"])

    def test_script_and_title_text_never_count_as_content(self):
        flat = [t for texts in self.groups.values() for t in texts]
        self.assertNotIn("var q = \"Pergunta falsa?\";", flat)
        self.assertFalse([t for t in flat if "falsa" in t])
        self.assertFalse([t for t in flat if "Ignorar" in t])

    def test_an_unclosed_tag_does_not_derail_later_labels(self):
        self.assertIn("p.unclosed", self.groups)
        self.assertIn("span.label", self.groups)

    def test_questions_report_where_they_live(self):
        found = inv.questions(self.parser.groups)
        self.assertEqual(found, [("span.question", "Quantos diplomados ha?")])

    def test_stray_end_tag_is_ignored_not_crashed(self):
        p = inv.LeafText()
        p.feed("<body><p>ok</p></div></span><p>ainda ok</p></body>")
        flat = [t for texts in p.groups.values() for t in texts]
        self.assertEqual(flat, ["ok", "ainda ok"])


class RedactionTest(unittest.TestCase):
    def test_grouped_figures_are_redacted(self):
        # decision 1: no PORDATA values reach a committed report
        self.assertEqual(inv.redact("valor de 1 234 567 em 2020"),
                         "valor de <number> em 2020")

    def test_a_bare_year_survives(self):
        self.assertEqual(inv.redact("desde 1960"), "desde 1960")
