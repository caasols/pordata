// Key-based i18n: add a language by adding one STRINGS block (and its
// label in AREA_LABELS), then whitelist it in AVAILABLE. {n} / {m} are
// placeholders. Indicator names exist in PT and EN only (that is what
// PORDATA publishes); other UI languages show the EN name first and the
// PT original underneath.

type Strings = Record<string, string>;

// Stryker disable all: the language tables are content, not logic;
// mutating UI copy only generates unkillable string mutants.

export const STRINGS: Record<string, Strings> = {
  pt: {
    intro: 'Catálogo pesquisável dos <b>{n}</b> indicadores da {pordata} (Fundação Francisco Manuel dos Santos). Este índice contém apenas <b>metadados</b> — os valores estão nas páginas da PORDATA e nas fontes oficiais (INE, Eurostat, Banco de Portugal).',
    placeholder: 'ex.: envelhecimento, salário médio, rendas…',
    results: '{n} indicadores', showing: ' (a mostrar {m})',
    resultsOne: '1 indicador',
    removed: 'descontinuado', sources: 'Fontes', updated: 'atual.',
    loadfail: 'Não foi possível carregar o catálogo.',
    summaryFilter: 'Resumo',
    summaryTip: "Um dos indicadores que a PORDATA mostra no quadro-resumo de cada município ou país.",
    unit: 'unidade', chartSoon: 'gráfico em breve', openAt: 'Abrir na PORDATA', openDetail: 'Ver detalhe', notAvailable: 'n/d',
    searchLabel: 'Pesquisar indicadores', empty: 'Sem resultados para esta pesquisa.', clearFilters: 'Limpar filtros',
    langLabel: 'Idioma', themeLabel: 'Tema claro/escuro', sortLabel: 'Ordenar',
    sortRelevance: 'Relevância', sortAz: 'Nome A→Z', sortZa: 'Nome Z→A',
    sortNew: 'Mais recentes', sortOld: 'Mais antigos',
    building: ' (colheita em curso)', updatedAt: 'Atualizado: ',
    foot: 'Dados e curadoria: {pordata}, Fundação Francisco Manuel dos Santos, e respetivas fontes. Índice construído a partir das páginas públicas de indicadores; sem redistribuição de valores. Código e metadados: {repo} · {json} · {csv}',
  },
  en: {
    intro: "Searchable catalogue of the <b>{n}</b> indicators of {pordata} (Francisco Manuel dos Santos Foundation). This index holds <b>metadata only</b> — the values live on PORDATA's pages and at the official sources (INE, Eurostat, Banco de Portugal).",
    placeholder: 'e.g.: ageing, average wage, rents…',
    results: '{n} indicators', showing: ' (showing {m})',
    resultsOne: '1 indicator',
    removed: 'discontinued', sources: 'Sources', updated: 'upd.',
    loadfail: 'Could not load the catalogue.',
    summaryFilter: 'Summary',
    summaryTip: "One of the indicators PORDATA shows in the summary table for each municipality or country.",
    unit: 'unit', chartSoon: 'chart coming', openAt: 'Open on PORDATA', openDetail: 'View details', notAvailable: 'n/a',
    searchLabel: 'Search indicators', empty: 'No indicators match this search.', clearFilters: 'Clear filters',
    langLabel: 'Language', themeLabel: 'Light/dark theme', sortLabel: 'Sort',
    sortRelevance: 'Relevance', sortAz: 'Name A→Z', sortZa: 'Name Z→A',
    sortNew: 'Newest first', sortOld: 'Oldest first',
    building: ' (harvest in progress)', updatedAt: 'Updated: ',
    foot: 'Data and curation: {pordata}, Francisco Manuel dos Santos Foundation, and their sources. Built from the public indicator pages; no data values are redistributed. Code and metadata: {repo} · {json} · {csv}',
  },
  es: {
    intro: 'Catálogo consultable de los <b>{n}</b> indicadores de {pordata} (Fundación Francisco Manuel dos Santos). Este índice contiene solo <b>metadatos</b>: los valores están en las páginas de PORDATA y en las fuentes oficiales (INE, Eurostat, Banco de Portugal). Los nombres de los indicadores existen en portugués e inglés.',
    placeholder: 'p. ej.: envejecimiento, salario medio, alquileres…',
    results: '{n} indicadores', showing: ' (mostrando {m})',
    resultsOne: '1 indicador',
    removed: 'descatalogado', sources: 'Fuentes', updated: 'act.',
    loadfail: 'No se pudo cargar el catálogo.',
    summaryFilter: 'Resumen',
    summaryTip: "Uno de los indicadores que PORDATA muestra en el cuadro resumen de cada municipio o país.",
    unit: 'unidad', chartSoon: 'gráfico próximamente', openAt: 'Abrir en PORDATA', openDetail: 'Ver detalle', notAvailable: 'n/d',
    searchLabel: 'Buscar indicadores', empty: 'Ningún indicador coincide con esta búsqueda.', clearFilters: 'Borrar filtros',
    langLabel: 'Idioma', themeLabel: 'Tema claro/oscuro', sortLabel: 'Ordenar',
    sortRelevance: 'Relevancia', sortAz: 'Nombre A→Z', sortZa: 'Nombre Z→A',
    sortNew: 'Más recientes', sortOld: 'Más antiguos',
    building: ' (recolección en curso)', updatedAt: 'Actualizado: ',
    foot: 'Datos y curaduría: {pordata}, Fundación Francisco Manuel dos Santos, y sus fuentes. Construido a partir de las páginas públicas de indicadores; sin redistribución de valores. Código y metadatos: {repo} · {json} · {csv}',
  },
  fr: {
    intro: "Catalogue interrogeable des <b>{n}</b> indicateurs de {pordata} (Fondation Francisco Manuel dos Santos). Cet index ne contient que des <b>métadonnées</b> — les valeurs se trouvent sur les pages de PORDATA et auprès des sources officielles (INE, Eurostat, Banco de Portugal). Les noms des indicateurs existent en portugais et en anglais.",
    placeholder: 'ex. : vieillissement, salaire moyen, loyers…',
    results: '{n} indicateurs', showing: ' (affichage de {m})',
    resultsOne: '1 indicateur',
    removed: 'discontinué', sources: 'Sources', updated: 'màj',
    loadfail: 'Impossible de charger le catalogue.',
    summaryFilter: 'Résumé',
    summaryTip: "L'un des indicateurs que PORDATA affiche dans le tableau de synthèse de chaque municipalité ou pays.",
    unit: 'unité', chartSoon: 'graphique à venir', openAt: 'Ouvrir sur PORDATA', openDetail: 'Voir le détail', notAvailable: 'n/d',
    searchLabel: 'Rechercher des indicateurs', empty: 'Aucun indicateur ne correspond à cette recherche.', clearFilters: 'Effacer les filtres',
    langLabel: 'Langue', themeLabel: 'Thème clair/sombre', sortLabel: 'Trier',
    sortRelevance: 'Pertinence', sortAz: 'Nom A→Z', sortZa: 'Nom Z→A',
    sortNew: 'Plus récents', sortOld: 'Plus anciens',
    building: ' (collecte en cours)', updatedAt: 'Mis à jour : ',
    foot: "Données et curation : {pordata}, Fondation Francisco Manuel dos Santos, et leurs sources. Construit à partir des pages publiques des indicateurs ; aucune valeur n'est redistribuée. Code et métadonnées : {repo} · {json} · {csv}",
  },
  de: {
    intro: 'Durchsuchbarer Katalog der <b>{n}</b> Indikatoren von {pordata} (Stiftung Francisco Manuel dos Santos). Dieser Index enthält nur <b>Metadaten</b> — die Werte stehen auf den PORDATA-Seiten und bei den amtlichen Quellen (INE, Eurostat, Banco de Portugal). Die Indikatornamen liegen auf Portugiesisch und Englisch vor.',
    placeholder: 'z. B.: Alterung, Durchschnittslohn, Mieten…',
    results: '{n} Indikatoren', showing: ' (zeige {m})',
    resultsOne: '1 Indikator',
    removed: 'eingestellt', sources: 'Quellen', updated: 'Stand',
    loadfail: 'Der Katalog konnte nicht geladen werden.',
    summaryFilter: 'Übersicht',
    summaryTip: "Einer der Indikatoren, die PORDATA in der Übersichtstabelle jeder Gemeinde oder jedes Landes zeigt.",
    unit: 'Einheit', chartSoon: 'Diagramm folgt', openAt: 'Auf PORDATA öffnen', openDetail: 'Details ansehen', notAvailable: 'k. A.',
    searchLabel: 'Indikatoren suchen', empty: 'Keine Indikatoren passen zu dieser Suche.', clearFilters: 'Filter zurücksetzen',
    langLabel: 'Sprache', themeLabel: 'Helles/dunkles Design', sortLabel: 'Sortieren',
    sortRelevance: 'Relevanz', sortAz: 'Name A→Z', sortZa: 'Name Z→A',
    sortNew: 'Neueste zuerst', sortOld: 'Älteste zuerst',
    building: ' (Erhebung läuft)', updatedAt: 'Aktualisiert: ',
    foot: 'Daten und Kuratierung: {pordata}, Stiftung Francisco Manuel dos Santos, und ihre Quellen. Erstellt aus den öffentlichen Indikatorseiten; keine Weiterverbreitung von Werten. Code und Metadaten: {repo} · {json} · {csv}',
  },
  it: {
    intro: 'Catalogo consultabile dei <b>{n}</b> indicatori di {pordata} (Fondazione Francisco Manuel dos Santos). Questo indice contiene solo <b>metadati</b>: i valori si trovano sulle pagine di PORDATA e presso le fonti ufficiali (INE, Eurostat, Banco de Portugal). I nomi degli indicatori esistono in portoghese e inglese.',
    placeholder: 'es.: invecchiamento, salario medio, affitti…',
    results: '{n} indicatori', showing: ' (mostrando {m})',
    resultsOne: '1 indicatore',
    removed: 'dismesso', sources: 'Fonti', updated: 'agg.',
    loadfail: 'Impossibile caricare il catalogo.',
    summaryFilter: 'Sintesi',
    summaryTip: "Uno degli indicatori che PORDATA mostra nel quadro di sintesi di ogni comune o paese.",
    unit: 'unità', chartSoon: 'grafico in arrivo', openAt: 'Apri su PORDATA', openDetail: 'Vedi dettaglio', notAvailable: 'n/d',
    searchLabel: 'Cerca indicatori', empty: 'Nessun indicatore corrisponde a questa ricerca.', clearFilters: 'Cancella filtri',
    langLabel: 'Lingua', themeLabel: 'Tema chiaro/scuro', sortLabel: 'Ordina',
    sortRelevance: 'Rilevanza', sortAz: 'Nome A→Z', sortZa: 'Nome Z→A',
    sortNew: 'Più recenti', sortOld: 'Più vecchi',
    building: ' (raccolta in corso)', updatedAt: 'Aggiornato: ',
    foot: 'Dati e cura: {pordata}, Fondazione Francisco Manuel dos Santos, e le rispettive fonti. Costruito dalle pagine pubbliche degli indicatori; nessuna ridistribuzione di valori. Codice e metadati: {repo} · {json} · {csv}',
  },
};

export const AREA_LABELS: Record<string, Record<string, string>> = {
  portugal: { pt: 'Portugal', en: 'Portugal', es: 'Portugal',
              fr: 'Portugal', de: 'Portugal', it: 'Portogallo' },
  municipios: { pt: 'Municípios', en: 'Municipalities', es: 'Municipios',
                fr: 'Municipalités', de: 'Gemeinden', it: 'Comuni' },
  europa: { pt: 'Europa', en: 'Europe', es: 'Europa',
            fr: 'Europe', de: 'Europa', it: 'Europa' },
};

const LINKS: Record<string, string> = {
  pordata: '<a href="https://www.pordata.pt" rel="noopener">PORDATA</a>',
  repo: '<a href="https://github.com/caasols/pordata" rel="noopener">github.com/caasols/pordata</a>',
  json: '<a href="data/catalogue.json">catalogue.json</a>',
  csv: '<a href="data/catalogue.csv">catalogue.csv</a>',
};

export function translate(lang: string, key: string,
                          params?: Record<string, string>): string {
  let s = (STRINGS[lang] || STRINGS.pt)[key] || STRINGS.pt[key] || key;
  for (const [k, v] of Object.entries({ ...LINKS, ...(params || {}) }))
    s = s.split("{" + k + "}").join(v);
  return s;
}

// All EU official languages, native names. Selectable today: content
// (indicator names) exists in PT and EN only; the rest are greyed out
// until their UI strings and content story are ready.
export const ALL_LANGS: Array<[string, string]> = [
  ["pt", "Português"], ["en", "English"], ["bg", "Български"],
  ["cs", "Čeština"], ["da", "Dansk"], ["de", "Deutsch"],
  ["el", "Ελληνικά"], ["es", "Español"], ["et", "Eesti"],
  ["fi", "Suomi"], ["fr", "Français"], ["ga", "Gaeilge"],
  ["hr", "Hrvatski"], ["hu", "Magyar"], ["it", "Italiano"],
  ["lt", "Lietuvių"], ["lv", "Latviešu"], ["mt", "Malti"],
  ["nl", "Nederlands"], ["pl", "Polski"], ["ro", "Română"],
  ["sk", "Slovenčina"], ["sl", "Slovenščina"], ["sv", "Svenska"],
];

// Stryker restore all

export const AVAILABLE = new Set(["pt", "en"]);

/**
 * The language for this visit: `?lang=` first, then a stored choice,
 * then the browser, then English.
 *
 * The query parameter is what gives the English half an address. The
 * site advertises `og:locale:alternate en_GB` and `inLanguage: [pt, en]`
 * while language lived only in localStorage — so there was no English
 * URL to link, index or share, and the English names the project
 * invested in had no page. `hreflang` alternates point here.
 *
 * `scripts/build_detail_pages.py BOOT` implements this same order for
 * the pre-rendered pages; `lang.test.ts` pins the table both read from.
 */
export function initialLang(): string {
  let stored: string | null = null;
  try { stored = localStorage.getItem("lang"); } catch { /* private mode */ }
  let query: string | null = null;
  try {
    query = new URLSearchParams(location.search).get("lang");
  } catch { /* no location in some test environments */ }
  if (query && AVAILABLE.has(query)) return query;
  if (stored && AVAILABLE.has(stored)) return stored;
  const nav = (navigator.language || "pt").slice(0, 2).toLowerCase();
  return AVAILABLE.has(nav) ? nav : "en";
}
