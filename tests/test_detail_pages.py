"""A page per indicator (roadmap 15).

These pages are the first thing this project shows a visitor that is not
a search box, and they are generated rather than authored — so the tests
are about the properties a generated page has to hold: a real canonical
URL, provenance that says what the crosswalk actually found (including
when it found nothing), the revision caveat travelling *with* the
indicator per decision 5, and escaping, because every value on the page
comes from someone else's HTML.

Two of them exist for reasons that have nothing to do with the reader.
`write_if_changed` is what keeps 2,195 near-identical files out of git
history every night, and the theme tokens are read from the site's own
stylesheet so the two cannot drift — a page served in stale colours
would look fine and be wrong.
"""

import json
import pathlib
import unittest
from unittest import mock

from helpers import RepoCase, load_script

d = load_script("build_detail_pages")


def row(**over):
    base = {"id": 1, "area": "portugal", "name": "Taxa de natalidade",
            "name_en": "Birth rate", "fontes": ["INE", "PORDATA"],
            "ultima_atualizacao": "2026-03-13",
            "url": "https://www.pordata.pt/portugal/taxa-1",
            "harvested_at": "2026-08-24"}
    base.update(over)
    return base


def entry(**over):
    base = {"source": "INE", "candidates": ["0012328"], "n_candidates": 1,
            "n_exact": 1, "truncated": False, "exact_title": ["0012328"],
            "operation": "INE, Censos 2021", "operation_share": 1.0,
            "theme": "População", "theme_share": 1.0, "subthemes": ["Censos"],
            "geo_levels": ["Freguesia"], "periodicities": ["Decenal"],
            "confidence": "exact"}
    base.update(over)
    return base


def render(r=None, e=None, titles=None):
    return d.render(r or row(), e, titles or {}, "../../style.css?v=abc")


class AddressTest(unittest.TestCase):
    """Pre-rendered, because a catalogue whose claim is machine
    discoverability cannot have 2,195 indicators with no addresses."""

    def test_the_page_has_a_real_canonical_url(self):
        html = render()
        self.assertIn('<link rel="canonical" href="'
                      'https://caasols.github.io/pordata/indicador/'
                      'portugal/1/">', html)

    def test_the_path_carries_the_area_because_ids_repeat(self):
        self.assertNotEqual(d.page_path(row(area="portugal", id=1)),
                            d.page_path(row(area="municipios", id=1)))

    def test_the_page_is_an_index_so_the_url_needs_no_extension(self):
        self.assertEqual(d.page_path(row()).name, "index.html")

    def test_the_stylesheet_is_referenced_relatively(self):
        """The site is served from a project subpath, so an absolute
        /style.css resolves against the domain root and 404s."""
        self.assertIn('href="../../style.css?v=abc"', render())


class ContentTest(unittest.TestCase):
    def test_the_title_and_coverage_line_are_separate(self):
        html = render(row(title="Casamentos", breakdown="total e por sexo"))
        self.assertIn("<h1>Casamentos</h1>", html)
        self.assertIn("total e por sexo", html)

    def test_it_falls_back_to_the_full_name_when_the_split_was_refused(self):
        self.assertIn("<h1>Taxa de natalidade</h1>", render())

    def test_sources_and_date_are_shown(self):
        html = render()
        self.assertIn("INE, PORDATA", html)
        self.assertIn("2026-03-13", html)

    def test_the_click_out_to_pordata_survives(self):
        """The card stopped linking to pordata.pt, so this page is now
        the only route to the values that exist today."""
        self.assertIn('href="https://www.pordata.pt/portugal/taxa-1"',
                      render())

    def test_the_chart_slot_says_it_is_not_a_chart_yet(self):
        html = render()
        self.assertIn("Gráfico em breve", html)
        self.assertIn("Chart coming soon", html)

    def test_the_discontinued_chip_renders_when_the_page_is_gone(self):
        self.assertIn("descontinuado", render(row(removed=True)))

    def test_a_live_row_carries_no_discontinued_chip(self):
        self.assertNotIn("descontinuado", render())

    def test_the_featured_chip_reflects_the_quadro_resumo(self):
        self.assertIn("quadro-resumo", render(row(featured=["europa"])))


class RevisionTest(unittest.TestCase):
    """Decision 5: a caveat that does not travel with the series is a
    caveat nobody reads."""

    def test_the_note_is_rendered_with_the_indicator(self):
        html = render(row(revision="Os valores ainda não refletem a revisão."))
        self.assertIn("Os valores ainda não refletem a revisão.", html)
        # above the footer, not in it
        self.assertLess(html.index("ainda não refletem"), html.index("<footer"))

    def test_a_row_with_no_note_gets_no_empty_section(self):
        self.assertNotIn("Nota de revisão", render())


class ProvenanceTest(unittest.TestCase):
    """The section nothing else has: which INE series could answer this."""

    def test_it_names_the_operation_and_granularity(self):
        html = render(e=entry())
        self.assertIn("INE, Censos 2021", html)
        self.assertIn("Freguesia", html)
        self.assertIn("Decenal", html)

    def test_candidate_series_link_to_ine(self):
        html = render(e=entry(), titles={"0012328": "Taxa de desemprego (%)"})
        self.assertIn("https://www.ine.pt/xurl/indx/0012328/PT", html)
        self.assertIn("Taxa de desemprego (%)", html)

    def test_each_series_carries_its_machine_readable_route(self):
        """An id you cannot fetch from is a footnote. The JSON endpoint
        is the reason the crosswalk is worth having."""
        self.assertIn("pindica.jsp?op=2&amp;varcd=0012328", render(e=entry()))

    def test_it_explains_why_there_is_more_than_one(self):
        html = render(e=entry())
        self.assertIn("família", html)
        self.assertIn("escolher ao acaso", html)

    def test_a_long_family_is_capped_and_says_how_many_more(self):
        many = entry(candidates=[f"{n:07d}" for n in range(30)],
                     n_candidates=30)
        html = render(e=many)
        self.assertEqual(html.count('class="id"'), 12)
        self.assertIn("+18", html)

    def test_a_short_family_gets_no_more_line(self):
        self.assertNotIn("+0", render(e=entry()))

    def test_a_refusal_is_rendered_as_a_result_not_an_absence(self):
        """`crosswalk: null` is a claim — the matcher looked and refused.
        Showing nothing would read as "we never checked"."""
        html = render(e=None)
        self.assertIn("Sem correspondência no INE", html)
        self.assertIn("não temos a certeza", html)

    def test_a_refusal_shows_no_series_list(self):
        self.assertNotIn('class="series"', render(e=None))

    def test_an_id_with_no_cached_title_still_links(self):
        """The INE cache is optional input; a missing title degrades to
        the id rather than dropping the candidate."""
        self.assertIn("0012328", render(e=entry(), titles={}))


class StructuredDataTest(unittest.TestCase):
    def test_each_page_describes_itself_as_a_dataset(self):
        data = json.loads(d.json_ld(row(), None))
        self.assertEqual(data["@type"], "Dataset")
        self.assertEqual(data["name"], "Taxa de natalidade")
        self.assertIn("pordata.pt", data["isBasedOn"][0])

    def test_the_provider_is_the_ine_operation_when_one_is_known(self):
        data = json.loads(d.json_ld(row(), entry()))
        self.assertEqual(data["provider"]["name"], "INE, Censos 2021")

    def test_an_unmatched_row_claims_no_provider(self):
        self.assertNotIn("provider", json.loads(d.json_ld(row(), None)))

    def test_empty_fields_are_omitted_rather_than_serialised_as_null(self):
        data = json.loads(d.json_ld(row(name_en="", unit=""), None))
        self.assertNotIn("alternateName", data)
        self.assertNotIn("variableMeasured", data)

    def test_the_json_ld_block_is_valid_json_in_the_page(self):
        html = render(e=entry())
        block = html.split('application/ld+json">')[1].split("</script>")[0]
        self.assertEqual(json.loads(block)["@type"], "Dataset")


class EscapingTest(unittest.TestCase):
    """Every value here came out of someone else's HTML."""

    def test_markup_in_a_name_is_escaped(self):
        html = render(row(name='Taxa <script>alert(1)</script>'))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_quotes_in_a_url_cannot_break_out_of_the_attribute(self):
        html = render(row(url='https://x/"onmouseover="evil()'))
        self.assertNotIn('"onmouseover="evil()', html)

    def test_markup_in_a_revision_note_is_escaped(self):
        self.assertNotIn("<b>", render(row(revision="a <b>b</b>")))

    def test_markup_in_an_ine_title_is_escaped(self):
        html = render(e=entry(), titles={"0012328": "<img src=x onerror=1>"})
        self.assertNotIn("<img src=x", html)


class ScriptContextTest(unittest.TestCase):
    """JSON-LD sits inside a `<script>` element, where HTML escaping
    would corrupt the JSON and no escaping at all lets an indicator name
    close the element early. This was a real bug: the visible page was
    escaped and this block was not."""

    def test_a_name_cannot_close_the_script_element(self):
        payload = d.json_ld(row(name="x </script><img src=q onerror=1>"), None)
        self.assertNotIn("</script>", payload)
        self.assertNotIn("<img", payload)

    def test_the_json_still_parses_to_the_original_string(self):
        """Escaping that changed the data would trade one bug for
        another: the structured data is the machine-readable claim."""
        name = "x </script> y"
        self.assertEqual(json.loads(d.json_ld(row(name=name), None))["name"],
                         name)

    def test_line_separators_are_escaped_too(self):
        """U+2028 and U+2029 are valid JSON but terminate a statement in
        older JavaScript parsers."""
        self.assertNotIn("\u2028", d.escape_for_script('"a\u2028b"'))

    def test_ordinary_json_is_untouched(self):
        self.assertEqual(d.escape_for_script('{"a":1}'), '{"a":1}')

    def test_the_page_block_is_safe_end_to_end(self):
        html = render(row(name="</script><script>alert(1)</script>"))
        self.assertNotIn("<script>alert(1)</script>", html)


# What the generator needs out of site/src/index.css. Kept here as one
# constant so a fixture cannot quietly drift into "minimal enough to
# pass" while the real file grows.
FULL_CSS = (":root {\n  --background: white;\n}\n"
            ".dark {\n  --background: black;\n}\n"
            "@theme inline {\n"
            "  --radius-sm: calc(var(--radius) - 4px);\n"
            "  --radius-md: calc(var(--radius) - 2px);\n"
            "  --radius-lg: var(--radius);\n"
            '  --font-sans: "Public Sans", ui-sans-serif, sans-serif;\n'
            "}\n")


class ThemeTest(RepoCase):
    """One source of truth for the colours."""

    def write_css(self, body):
        path = pathlib.Path("index.css")
        path.write_text(body, encoding="utf-8")
        return path

    def test_it_reads_the_tokens_out_of_the_site_stylesheet(self):
        css = self.write_css(FULL_CSS)
        got = d.theme_tokens(css)
        self.assertIn("--background: white", got)
        self.assertIn("--background: black", got)

    def test_it_lifts_the_radius_scale_and_the_font_stack(self):
        """Colours were never the only thing shared. A hand-written
        radius or a four-item subset of the font stack is the same drift
        in a different property."""
        got = d.theme_tokens(self.write_css(FULL_CSS))
        self.assertIn("--radius-sm", got)
        self.assertIn("--radius-lg", got)
        self.assertIn("--font-sans", got)
        self.assertIn("Public Sans", got)

    def test_a_missing_font_stack_fails_the_build_loudly(self):
        """Without it the pages render in the system sans and look like a
        different site next to the index — which is what happened."""
        css = self.write_css(FULL_CSS.replace("  --font-sans:", "  --other:"))
        with self.assertRaises(SystemExit):
            d.theme_tokens(css)

    def test_a_missing_block_fails_the_build_loudly(self):
        """A silent fallback copy would serve pages in stale colours and
        look completely fine."""
        css = self.write_css(":root {\n  --background: white;\n}\n")
        with self.assertRaises(SystemExit):
            d.theme_tokens(css)


def meta_block(html):
    return html.split('<div class="meta">')[1].split("</div></div>")[0]


class StableLayoutTest(unittest.TestCase):
    """Every page has the same shape, whatever the row is missing.

    The card hit this first: dropping an empty cell let the remaining
    fields slide up into its place, so a field sat in a different
    position on every indicator and the whole block jumped as you moved
    between them. The detail page shipped with the same defect. The
    invariant is the card's — reserve the row, keep the label, dim the
    value — so it is asserted the same way.
    """

    FIELDS = 5      # sources, updated, unit, area, name_en

    def cells_in(self, html):
        return html.count('class="field'), html.count('class="k"')

    def test_a_row_with_no_unit_still_reserves_it(self):
        """The unit is genuinely absent on 48% of rows. That is the
        common case, not the edge case."""
        block = meta_block(render(row(unit="")))
        self.assertEqual(self.cells_in(block), (self.FIELDS, self.FIELDS))

    def test_a_full_row_has_exactly_the_same_shape(self):
        self.assertEqual(
            self.cells_in(meta_block(render(row(unit="Taxa - %")))),
            self.cells_in(meta_block(render(row(unit="")))))

    def test_the_fields_keep_their_order(self):
        """Order is the other half of stability: same count in a
        different sequence still moves everything."""
        def labels(html):
            block = meta_block(html)
            return [chunk.split("</span>")[0]
                    for chunk in block.split('<span class="k">')[1:]]
        self.assertEqual(labels(render(row(unit=""))),
                         labels(render(row(unit="Taxa - %"))))

    def test_a_missing_value_shows_a_dimmed_placeholder(self):
        """A blank cell reads as a rendering fault; a labelled `n/d`
        reads as 'PORDATA does not publish one'."""
        html = render(row(unit=""))
        self.assertIn('<span class="na">', html)
        self.assertIn("n/d", html)
        self.assertIn("n/a", html)

    def test_the_placeholder_is_dimmer_than_a_real_value(self):
        na = d.STYLESHEET.split(".na{")[1].split("}")[0]
        self.assertIn("opacity:.5", na)

    def test_the_columns_are_fixed_not_auto_fitting(self):
        """`auto-fit` was the mechanism: it repacked the columns as soon
        as a field disappeared."""
        rule = d.STYLESHEET.split(".meta{")[1].split("}")[0]
        self.assertNotIn("auto-fit", rule)
        self.assertIn("repeat(3,minmax(0,1fr))", rule)

    def test_long_fields_span_the_row_by_declaration_not_by_length(self):
        """`fontes` and the English name are sentences and always span.
        Deciding that from the value would put the layout back at the
        mercy of the data — a short source string would sit in a
        one-third cell on one page and a full row on the next."""
        short = render(row(fontes=["INE"], name_en="X"))
        long_ = render(row(fontes=["A", "B", "C", "D"], name_en="Y" * 90))
        self.assertEqual(meta_block(short).count('class="field wide"'),
                         meta_block(long_).count('class="field wide"'))
        self.assertEqual(meta_block(short).count('class="field wide"'), 2)


class DesignSystemTest(unittest.TestCase):
    """The detail page and the card have to read as one design.

    The first version of this stylesheet was hand-written from memory
    rather than from the components, and it showed on a phone: the card's
    area badge is a grey `secondary` pill and the detail page's was
    primary orange, the card's meta value is 12px and the page's was the
    16px body size. These assert against the components themselves, so a
    variant changing in `badge.tsx` fails here instead of quietly leaving
    two designs on one site.
    """

    SITE = pathlib.Path(__file__).resolve().parents[1] / "site" / "src"

    def sheet(self):
        return d.STYLESHEET

    def test_the_chip_uses_the_badge_default_variant(self):
        badge = (self.SITE / "components" / "ui" / "badge.tsx").read_text(
            encoding="utf-8")
        # the variant the component falls back to when none is passed,
        # which is what the card's area badge renders as
        self.assertIn('defaultVariants: { variant: "secondary" }', badge)
        self.assertIn("bg-secondary text-secondary-foreground", badge)
        self.assertIn("background:var(--secondary)", self.sheet())
        self.assertIn("color:var(--secondary-foreground)", self.sheet())

    def test_the_chip_is_not_a_primary_pill(self):
        """What the screenshot caught: orange where the card is grey."""
        chip = self.sheet().split(".chip{")[1].split("}")[0]
        self.assertNotIn("--primary", chip)
        self.assertNotIn("999px", chip)

    def test_the_meta_label_matches_the_card_exactly(self):
        app = (self.SITE / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("text-[9.5px] uppercase tracking-[0.1em]", app)
        label = self.sheet().split(".field .k{")[1].split("}")[0]
        self.assertIn("font-size:9.5px", label)
        self.assertIn("letter-spacing:.1em", label)

    def test_the_meta_value_is_near_the_card_not_body_size(self):
        """A page is read rather than scanned, so one step up from the
        card's text-xs is deliberate — the 16px body size was not."""
        value = self.sheet().split(".field .v{")[1].split("}")[0]
        self.assertIn("font-size:.8125rem", value)

    def test_radii_come_from_the_lifted_scale(self):
        """`rounded-sm` and `rounded-lg` are what Badge and Card use, so
        the page has to speak the same scale rather than pick numbers."""
        for token in ("--radius-sm", "--radius-lg"):
            self.assertIn(f"var({token})", self.sheet())

    def test_the_radius_scale_is_lifted_not_recomputed(self):
        tokens = d.theme_tokens()
        for name in ("--radius-sm", "--radius-md", "--radius-lg"):
            self.assertIn(name, tokens)

    def test_the_font_is_loaded_not_merely_named(self):
        """Naming "Public Sans" in a stack does not load it. The pages
        fell through to the system sans and read as a different site."""
        index = (self.SITE.parent / "index.html").read_text(encoding="utf-8")
        self.assertIn("fonts.googleapis.com/css2?family=Public+Sans", index)
        self.assertIn("fonts.googleapis.com/css2?family=Public+Sans",
                      d.FONT_LINKS)
        self.assertIn("fonts.gstatic.com", d.FONT_LINKS)

    def test_the_body_uses_the_lifted_stack_not_a_subset(self):
        body = self.sheet().split("body{")[1].split("}")[0]
        self.assertIn("var(--font-sans)", body)
        self.assertNotIn("Public Sans", body)

    def test_the_cta_is_the_only_button_variant_this_site_has(self):
        """button.tsx offers `outline` and `ghost` and defaults to
        outline. There is no filled primary variant anywhere, so an
        orange filled CTA was inventing an idiom — the same mistake as
        the orange pill, one element along."""
        button = (self.SITE / "components" / "ui" / "button.tsx").read_text(
            encoding="utf-8")
        self.assertIn('defaultVariants: { variant: "outline"', button)
        self.assertNotIn("bg-primary", button)
        cta = self.sheet().split(".cta{")[1].split("}")[0]
        self.assertNotIn("--primary", cta)
        self.assertIn("background:transparent", cta)
        self.assertIn("var(--border)", cta)

    def test_the_shadow_is_the_compiled_shadow_xs_value(self):
        """Guessed as 0 1px 2px -1px / .08; Tailwind compiles shadow-xs
        to 0 1px 2px 0 #0000000d."""
        built = sorted((self.SITE.parents[1] / "docs" / "assets").glob("*.css"))
        self.assertTrue(built, "no built stylesheet to check against")
        compiled = built[0].read_text(encoding="utf-8")
        self.assertIn("--tw-shadow:0 1px 2px 0 var(--tw-shadow-color,#0000000d)",
                      compiled)
        self.assertIn("box-shadow:0 1px 2px 0 #0000000d", self.sheet())

    def test_focusable_things_get_a_ring_like_the_spa(self):
        """The SPA rings every focusable control; these pages had the
        browser default, which is inconsistent and worse."""
        app = (self.SITE / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("focus-visible:ring-[3px]", app)
        self.assertIn("a:focus-visible", self.sheet())
        self.assertIn("var(--ring)", self.sheet())

    def test_the_theme_boot_matches_the_spa_exactly(self):
        """`t !== "light"`, not `!t`: an unset *or unrecognised* value
        follows the system preference, and an explicit light beats a dark
        system. Two different rules would flip appearance on crossing."""
        index = (self.SITE.parent / "index.html").read_text(encoding="utf-8")
        self.assertIn('t !== "light"', index)
        self.assertIn('t!=="light"', d.BOOT)

    def test_the_h1_matches_the_spa_heading_scale(self):
        app = (self.SITE / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("text-2xl font-bold tracking-tight", app)
        h1 = self.sheet().split("h1{")[1].split("}")[0]
        self.assertIn("font-size:1.5rem", h1)     # text-2xl
        self.assertIn("font-weight:700", h1)      # font-bold
        self.assertIn("letter-spacing:-.025em", h1)  # tracking-tight

    def test_the_card_wrapper_matches_the_component(self):
        card = (self.SITE / "components" / "ui" / "card.tsx").read_text(
            encoding="utf-8")
        self.assertIn("rounded-lg border border-border bg-card", card)
        block = self.sheet().split(".card{")[1].split("}")[0]
        self.assertIn("var(--radius-lg)", block)
        self.assertIn("var(--border)", block)
        self.assertIn("var(--card)", block)


class ChurnTest(RepoCase):
    """2,195 files rewritten nightly is megabytes of identical HTML in
    git history for nothing."""

    def test_an_unchanged_file_is_not_rewritten(self):
        path = pathlib.Path("p.html")
        self.assertTrue(d.write_if_changed(path, "a"))
        self.assertFalse(d.write_if_changed(path, "a"))

    def test_a_changed_file_is_rewritten(self):
        path = pathlib.Path("p.html")
        d.write_if_changed(path, "a")
        self.assertTrue(d.write_if_changed(path, "b"))
        self.assertEqual(path.read_text(encoding="utf-8"), "b")

    def test_it_creates_the_directory_it_needs(self):
        self.assertTrue(d.write_if_changed(pathlib.Path("a/b/c.html"), "x"))


class BuildTest(RepoCase):
    def setUp(self):
        super().setUp()
        pathlib.Path("site/src").mkdir(parents=True)
        pathlib.Path("site/src/index.css").write_text(
            FULL_CSS, encoding="utf-8")
        patch = mock.patch.object(d, "THEME_CSS",
                                  pathlib.Path("site/src/index.css"))
        patch.start()
        self.addCleanup(patch.stop)
        self.rows = [row(id=1, area="portugal"), row(id=1, area="municipios")]
        self.crosswalk = {"portugal/1": entry()}

    def build(self):
        return d.build(self.rows, self.crosswalk, {}, pathlib.Path("out"))

    def test_it_writes_one_page_per_indicator_plus_the_stylesheet(self):
        stats = self.build()
        self.assertEqual(stats["pages"], 2)
        self.assertEqual(stats["written"], 3)
        self.assertTrue(pathlib.Path("out/portugal/1/index.html").exists())
        self.assertTrue(pathlib.Path("out/municipios/1/index.html").exists())
        self.assertTrue(pathlib.Path("out/style.css").exists())

    def test_a_second_run_writes_nothing(self):
        self.build()
        self.assertEqual(self.build()["written"], 0)

    def test_only_the_changed_page_is_rewritten(self):
        self.build()
        self.rows[0]["name"] = "Outro nome"
        self.assertEqual(self.build()["written"], 1)

    def test_it_counts_how_many_pages_carry_provenance(self):
        self.assertEqual(self.build()["with_crosswalk"], 1)

    def test_the_stylesheet_version_changes_with_the_stylesheet(self):
        """Pages reference style.css?v=<hash>, so a token change has to
        bust the cache or readers keep the old colours."""
        first = self.build()["css_version"]
        pathlib.Path("site/src/index.css").write_text(
            FULL_CSS.replace("--background: white", "--background: pink"),
            encoding="utf-8")
        self.assertNotEqual(self.build()["css_version"], first)

    def test_a_row_the_crosswalk_never_saw_still_gets_a_page(self):
        html = pathlib.Path("out/municipios/1/index.html")
        self.build()
        self.assertIn("Sem correspondência", html.read_text(encoding="utf-8"))


class StrictTest(RepoCase):
    """Every card links here, so a missing page is a 404 a visitor meets."""

    def setUp(self):
        super().setUp()
        pathlib.Path("out/portugal/1").mkdir(parents=True)
        pathlib.Path("out/portugal/1/index.html").write_text("x",
                                                             encoding="utf-8")

    def test_a_complete_build_reports_nothing_missing(self):
        self.assertEqual(
            d.missing_pages([row(id=1, area="portugal")],
                            pathlib.Path("out")), [])

    def test_a_row_with_no_page_is_named(self):
        got = d.missing_pages([row(id=1, area="portugal"),
                               row(id=2, area="europa")], pathlib.Path("out"))
        self.assertEqual(got, ["europa/2"])

    def test_it_checks_disk_rather_than_trusting_the_return_value(self):
        """The build could report success and still have written nothing
        — what matters is the file a request would hit."""
        pathlib.Path("out/portugal/1/index.html").unlink()
        self.assertEqual(
            d.missing_pages([row(id=1, area="portugal")],
                            pathlib.Path("out")), ["portugal/1"])


class SitemapTest(unittest.TestCase):
    """Pre-rendering buys nothing a crawler cannot reach."""

    def test_every_row_gets_a_url(self):
        xml = d.sitemap([row(id=1), row(id=2, area="europa")])
        self.assertEqual(xml.count("<url>"), 2)
        self.assertIn("indicador/europa/2/", xml)

    def test_lastmod_is_the_indicator_date_not_the_build_date(self):
        """Stamping today on 2,195 URLs every night tells a crawler
        everything changed when nothing did, and it stops believing the
        field."""
        self.assertIn("<lastmod>2026-03-13</lastmod>", d.sitemap([row()]))

    def test_a_non_iso_date_is_omitted_rather_than_emitted_invalid(self):
        for bad in ("", "n/d", "2026", "13/03/2026"):
            with self.subTest(bad):
                self.assertNotIn(
                    "<lastmod>", d.sitemap([row(ultima_atualizacao=bad)]))

    def test_it_is_well_formed_xml(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(d.sitemap([row(name="a & b <c>")]))
        self.assertTrue(root.tag.endswith("urlset"))


class IneTitlesTest(RepoCase):
    def test_a_missing_cache_is_not_fatal(self):
        """The ids still link; they just read as ids."""
        self.assertEqual(d.ine_titles(pathlib.Path("nope.csv")), {})

    def test_it_maps_id_to_title(self):
        path = pathlib.Path("ine.csv")
        path.write_text(
            "id,dates,description,geo_lastlevel,html,json,keywords,"
            "periodicity,source,subtheme,theme,title,update_type,varcd\n"
            "0000001,d,desc,Portugal,h,j,k,Anual,s,sub,tema,Casamentos,A,1\n",
            encoding="utf-8")
        self.assertEqual(d.ine_titles(path), {"0000001": "Casamentos"})


if __name__ == "__main__":
    unittest.main()
