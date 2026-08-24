# Upstream reuse terms — what the pages actually say (roadmap 13)

Fetched by `scripts/spike_licences.py` via Actions, because this sandbox has no route to any of the three. **Nothing here is a decision.** Item 13 asks for four things per source — licence name, URL, the exact attribution string it requires, and whether it permits redistributing *derived* series rather than merely displaying them — and all four are judgements about a legal document. They stay the owner's. This is the reading material, quoted in the source's own words, so the call can be made in minutes instead of half an hour of hunting.

Candidate URLs, not addresses: nobody knew the current terms page for any of the three, so every outcome is recorded — including the misses. A 404 here means the guess was wrong, never that a source has no terms.

**The archive job (item 14) refuses to write any series whose source has no recorded entry.** That gate is the reason this is worth half an hour of anyone's attention.

## INE

- **MISS** `https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_princ_termos` — status 403, 0 KB — HTTP 403
- **MISS** `https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_cont_inst&INST=6251013` — status 403, 0 KB — HTTP 403
- **MISS** `https://www.ine.pt/` — status 403, 0 KB — HTTP 403

No sentence on any INE candidate matched the reuse/licence vocabulary. That is a result about these URLs, not about the source — read the saved front page for the real link.


## Eurostat

- **MISS** `https://ec.europa.eu/eurostat/about-us/policies/copyright` — status 404, 0 KB — HTTP 404
- **ok** `https://commission.europa.eu/legal-notice_en` — status 200, 149 KB
  - title: Legal notice - European Commission
- **ok** `https://ec.europa.eu/eurostat` — status 200, 236 KB
  - title: Home - Eurostat

### Eurostat — sentences that mention reuse, licensing or attribution

- Home Legal notice Legal notice The information on this site is subject to a disclaimer and copyright notice.
  - *from* `https://commission.europa.eu/legal-notice_en`
- Privacy policy Copyright notice © European Union, 1995-2026 The Commission's reuse policy is implemented by the Commission Decision of 12 December 2011 on the reuse of Commission documents .
  - *from* `https://commission.europa.eu/legal-notice_en`
- in individual copyright notices), content owned by the EU on this website is licensed under the Creative Commons Attribution 4.0 International (CC BY 4.0) licence .
  - *from* `https://commission.europa.eu/legal-notice_en`
- This means that reuse is allowed, provided appropriate credit is given and changes are indicated.
  - *from* `https://commission.europa.eu/legal-notice_en`
- Software or documents covered by industrial property rights, such as patents, trade marks, registered designs, logos and names, are excluded from the Commission's reuse policy and are not licensed to you.
  - *from* `https://commission.europa.eu/legal-notice_en`

## BPstat

- **ok** `https://bpstat.bportugal.pt/conteudos/quem-somos` — status 200, 4 KB
  - title: BPstat
- **ok** `https://bpstat.bportugal.pt/` — status 200, 104 KB
  - title: BPstat
- **MISS** `https://www.bportugal.pt/pagina/termos-e-condicoes` — status 403, 0 KB — HTTP 403

No sentence on any BPstat candidate matched the reuse/licence vocabulary. That is a result about these URLs, not about the source — read the saved front page for the real link.


## Record the outcome in `context.md` item 13

For each source: licence name, its URL, the exact attribution string, and redistribution-of-derived-series yes/no. Then item 14 can be built, and its licence registry stops refusing.
