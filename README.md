# The World of Svellheim

[Open the illustrated World Gazetteer (PDF)](output/pdf/Svellheim-World-Gazetteer.pdf)

Book One is a system-agnostic guide to Svellheim.

Svellheim once prospered. Ships sailed south, assemblies drew delegates from across the land, and even in the far north people knew when to expect summer. Now the deep winter has settled in. Communities share what warmth they can spare and contend with the things that are poisoning the land.

- [Foreword](editorial/foreword.md)
- [A History of Svellheim](gazetteer/03-history.md)
- [The Age of Embers](gazetteer/01-the-age-of-embers.md)
- [Atlas of Svellheim](gazetteer/04-atlas.md)
- [Hrafnborg](gazetteer/02-hrafnborg.md)
- [The Peoples of Svellheim](gazetteer/05-ancestries.md)
- [The Gods of Svellheim](gazetteer/06-pantheon.md)
- [A Companion to Svellheim](gazetteer/07-reckonings.md)

## Stories of Svellheim

[Read the short story collection (PDF)](output/pdf/Stories-of-Svellheim.pdf)

1. [To live with the dead](stories/01-to-live-with-the-dead.md)
2. [The Miller’s Heel](stories/02-the-millers-heel.md)
3. [The Key in the Roof](stories/03-the-key-in-the-roof.md)
4. [Places in the Boat](stories/04-places-in-the-boat.md)
5. [Seven Notches](stories/05-seven-notches.md)
6. [The Spare Bed](stories/06-the-spare-bed.md)
7. [A Name in Wool](stories/07-a-name-in-wool.md)

The [manuscript archive](stories/archive/) keeps the earlier historical accounts, household traditions, winter scenes and accounts of worship.

## Manuscript format

Write chapters, editorial notes, and map guides in Markdown (`.md`). When adapting material from the older AsciiDoc campaign books, convert its headings, tables, and links to Markdown. The Markdown manuscript is the source for the planned PDF edition.

## Illustrated edition

The [production script](production/build_book.py) sets the illustrated gazetteer in two columns on US Letter pages. The companion uses a six-by-nine-inch fiction trim with a single column, indented paragraphs and art on the cover. Rebuild both with `python3 production/build_book.py` on this system. The local PDFCraft CLI finishes the PDFs. Original illustration assets and the transparent wordmark are in [artwork](artwork/).
