# Team member profile URLs — inventory & what's still needed

Context: `/team/` cards show icon-link buttons per member for LinkedIn, Google
Scholar, ResearchGate, ORCID, personal site, CV. When a profile URL is in the
source content (Weebly export), the parser already surfaces it as an icon.

This file tracks what the repo has vs. what the user still needs to supply
manually. No web searches were performed — the sub-agent was denied internet
access, so everything below is harvested from existing repo content only.

## Already populated from repo content

| Member                    | Scholar | LinkedIn | ResearchGate | ORCID | Other |
|---------------------------|:-------:|:--------:|:------------:|:-----:|-------|
| Lucie Berkovitch          | ✅      |          |              |       |       |
| Cordelia Erickson-Davis   |         |          | ✅           |       |       |
| Polona Pozeg              |         | ✅       |              |       |       |
| Leor Roseman              |         |          | ✅           |       |       |
| Enzo Tagliazucchi         |         |          | ✅           |       |       |
| Chris Timmermann          |         |          | ✅           |       |       |
| Paweł Motyka              | ✅ (manual) |     |              |       |       |

Plus the following *personal-site* links were already classified as `site`
icons on their cards: Aviva Berkovitch-Ohana (Haifa), Maddalena Canna (CEU),
Anna Ciaunica, Cyriel Costines (costines.info + altered X project + contemplative-lab.de),
Guillaume Dumas (unicog.org), Tom Froese, Romy Lorenz (romylorenz.com),
Selen Atasoy (selenatasoy.com), Arnaud Halloy (blogspot), Alice Guyon (wixsite),
Juan González (academia.edu), Raphaël Millière (Cornell philosophy), Katrin Preller (uzh.ch).

## Missing (needs manual input from you)

For each of the **remaining 36 members** please provide any you have for:
- Google Scholar profile URL (e.g. `https://scholar.google.com/citations?user=…`)
- LinkedIn URL (e.g. `https://www.linkedin.com/in/…`)
- ORCID iD (e.g. `https://orcid.org/0000-0000-0000-0000`)

Names (alphabetical; the ones with some data already filled are starred but I'll
take more for each):

```
Selen Atasoy* (site)          Tom Froese* (site)               Charlotte Martial
Edvard Aviles                 Juan González* (academia)        Audrey Mazancieux
Aviva Berkovitch-Ohana*       Alice Guyon* (site)              Raphaël Millière* (site)
Lucie Berkovitch* (scholar)   Arnaud Halloy* (blog)            Paweł Motyka* (scholar)
Alexandre Billon              Matthieu Koroma                  Polona Pozeg* (linkedin)
Alessio Bucci                 France Lerner                    Katrin Preller* (site)
Maddalena Canna* (site)       Michael Lifshitz                 Leor Roseman* (researchgate)
Anna Ciaunica* (site)         Romy Lorenz* (site)              Matthew Sacchet
Cyriel Costines* (3 sites)    Cécile Manhich                   Timo Torsten Schmidt
Léna Coutrot                                                    Rebecca Seligman
Guillaume Dumas* (site)                                         François Tadel
David Dupuis                                                    Enzo Tagliazucchi* (researchgate)
Sebastian Ehmann                                                Chris Timmermann* (researchgate)
Michiel van Elk                                                 Cordelia Erickson-Davis* (researchgate)
Mar Estarellas                                                  Mathieu Frerejouan
George Fejer                                                    Daniel Friedman
Brendan Fleig-Goldstein                                         Larry D. Fort
```

## Quick-paste format

Preferred input format (one line per URL, comma-separated):
```
Selen Atasoy, scholar, https://scholar.google.com/citations?user=...
Selen Atasoy, orcid,   https://orcid.org/0000-...
George Fejer, linkedin, https://www.linkedin.com/in/george-fejer...
```

Once you drop that block into a message, I'll fold them into the team-cards
build script (`tools/minify/rebuild-team-cards.py`, in a `PROFILE_URLS` dict
keyed by normalized name) and every matching member's card gets the new icon
button automatically on the next rebuild.
