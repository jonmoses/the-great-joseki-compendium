# The Great Joseki Compendium

A Go opening dictionary built from what people actually play. It holds 6,581 corner
positions and 669 settled lines, counted from 1.2 million ranked 19×19 games on
[OGS](https://online-go.com), with how often each one is played in four rank bands:
15k–10k, 9k–5k, 4k–1k, and 1d and up.

It answers two questions a normal joseki dictionary does not:

- **Which sequences will I meet at my rank?**
- **At what rank does a sequence start to appear?**

The data is public domain (CC0). Use it for study, in an app, in a bot, in a paper, with or
without credit.

## What is in the repo

| Path | What it is |
| --- | --- |
| `index.html` | A viewer: click through the tree and see each move's share in each band. [Open it here](https://jonmoses.github.io/the-great-joseki-compendium/) |
| `data/joseki.json` | Every position, its counts in each band, and its follow-ups |
| `data/lines.csv` | The 669 settled lines as a flat table, for a spreadsheet |
| `sgf/*.sgf` | One variation tree per first corner move, for any SGF editor |
| `examples/` | Lookup helpers in Python and JavaScript |
| `scripts/` | The three scripts that built everything from the game dump |

## Reading a sequence

`X4-4 O3-6 X6-3 O2-4 X3-3 O3-9`

- `X` is the side that played first in the corner. `O` is the other side. Colour is ignored.
- `4-4` is a point: 4 lines from one edge and 4 from the other. `3-6` and `6-3` are mirror
  images, so every sequence is stored in one orientation (the one that sorts first).
- Two moves in a row by the same side (`X4-4 X3-6`) mean the other side played elsewhere.

The SGF files put the corner in the upper right, with `X` as Black.

## What the numbers mean

- **`per10k`** is how many times the position was reached per 10,000 corners in a band.
  A game has four corners, so 25 per 10,000 is about once in 100 games.
- **`settled_share`** is how often play left the corner at exactly this position. A position
  is marked as a **line** when that share is 25% or more and it has at least three stones.
- **`peak_band`** is the band where the position is most common.
- **`first_band`** is the weakest band where it reaches a third of its peak share. Read it
  as "this is where it starts to show up".

The raw counts are included, so you can apply your own rules.

| Band | Games | Corners | Lines first common here |
| --- | ---: | ---: | ---: |
| 15k–10k | 516,068 | 2,059,233 | 475 |
| 9k–5k | 428,052 | 1,709,558 | 90 |
| 4k–1k | 213,715 | 854,027 | 74 |
| 1d+ | 56,122 | 224,314 | 30 |

## How it was compiled

1. **Source.** The 2021 OGS game dump on the
   [Internet Archive](https://archive.org/details/ogs2021): 27 million games, collected by
   Zachary Vance with OGS's permission.
2. **Games kept.** 19×19, ranked, even (no handicap), finished, 30 moves or more, started
   between January 2018 and August 2021, and both players in the same rank band. Ranks are
   the players' OGS ranks at the time of the game.
3. **Bots removed.** The dump has no bot flag. Accounts were dropped when their name matched
   a list of bot words, or when they played more than 2,994 qualifying games (446 accounts).
4. **Corner sequences.** For each corner, the stones played in its 9×9 quadrant during the
   first 100 moves, in order, up to 24 stones. A sequence ends when the corner goes quiet for
   more than 8 moves, once three stones are down.
5. **One orientation.** Each sequence is mapped to one corner and one diagonal mirror, and
   the first side to play is named `X`.
6. **Pruning.** A position is kept when, in at least one band, it was reached 50 times and
   at least once per 10,000 corners. Its follow-ups are counted only if it was kept.

## Limits

- **Common is not the same as correct.** Nothing here was checked against a joseki book or
  an engine. Popular mistakes are in the data, mostly in the weaker bands.
- **The corner is read alone.** Stones on the sides and in other corners are ignored, so
  the data cannot say when a line depends on a ladder or a nearby stone.
- **Move order matters.** Two orders that reach the same position are stored as two
  sequences.
- **The games end in August 2021.** Later fashions are missing.
- **The dan band is small.** It has a tenth of the games of the weakest band, so its rare
  lines are noisier.
- **New accounts are mixed in.** A new OGS account starts near the middle of the scale, so
  some players in a band were not really of that rank.
- **Bot removal is a heuristic.** Some bots may remain and some very active people were
  dropped.

## Using it

**Look a position up (Python):**

```python
from examples.lookup import load, key

book = load('data/joseki.json')
# moves on a full board: (colour, column, row), counted from 0 at the top left
k = key([('B', 15, 3), ('W', 16, 5), ('B', 13, 2)])
print(k)                               # X4-4 O3-6 X6-3
print(book['positions'][k]['per10k'])  # share in each band
print(book['positions'][k]['next'])    # the follow-ups, most common first
```

`examples/lookup.js` does the same in JavaScript.

**Rebuild from the dump** (about 20 GB to download, an hour to run):

```sh
python3 scripts/corners.py ogs_games_2013_to_2021-08.json.gz corners.tsv
python3 scripts/build.py corners.tsv tree.json 1 50
python3 scripts/export.py tree.json .
```

The two numbers passed to `build.py` are the pruning thresholds. The bands and the date
range are constants at the top of `build.py`.

## Licence

- **Data** (`data/`, `sgf/`): [CC0 1.0](LICENSE-DATA), public domain.
- **Code** (`scripts/`, `examples/`, `index.html`): [MIT](LICENSE-CODE).

## Thanks

To OGS for the games and for permitting the dump, and to Zachary Vance for collecting it.
