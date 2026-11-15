# The Great Joseki Compendium

A Go opening dictionary built from what people actually play. It holds 6,280 corner
positions and 643 settled lines, counted from 1.2 million ranked 19×19 games on
[OGS](https://online-go.com), with how often each one is played in four rank bands:
15k–10k, 9k–5k, 4k–1k, and 1d and up. Every position is scored by KataGo, and the 140
sequences that leave one side 4 or more points behind are taken out and listed as mistakes.

It answers three questions a normal joseki dictionary does not:

- **Which sequences will I meet at my rank?**
- **At what rank does a sequence start to appear?**
- **Which popular moves at my rank are mistakes, and what do they cost?**

The data is public domain (CC0). Use it for study, in an app, in a bot, in a paper, with or
without credit.

## What is in the repo

| Path | What it is |
| --- | --- |
| `index.html` | A viewer with two modes. **Explore**: click through the tree and see each move's share in each band and KataGo's view of it. **Practice**: play a line from memory. [Open it here](https://jonmoses.github.io/the-great-joseki-compendium/) |
| `STUDY.md` | For each band, the 30 lines played most and the 15 most common mistakes |
| `data/joseki.json` | Every position: counts in each band, KataGo score, win rate, yearly trend, follow-ups |
| `data/lines.csv` | The 643 settled lines as a flat table, for a spreadsheet |
| `data/mistakes.json`, `data/mistakes.csv` | The 140 sequences that were taken out, with what each costs and what KataGo plays instead |
| `sgf/*.sgf` | One variation tree per first corner move, for any SGF editor |
| `examples/` | Lookup helpers in Python and JavaScript |
| `scripts/` | The four scripts that built everything from the game dump |

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

- **`per10k_by_year`** is the same share for 2018, 2019, 2020 and 2021 (to August), all
  bands together. It shows what was coming into or going out of fashion.
- **`x_win_rate`** is the share of games `X` went on to win, per band, among games that
  ended by resignation or by counting. It is left empty below 200 such games.

The raw counts are included, so you can apply your own rules.

| Band | Games | Corners | Lines first common here |
| --- | ---: | ---: | ---: |
| 15k–10k | 516,068 | 2,059,233 | 452 |
| 9k–5k | 428,052 | 1,709,558 | 90 |
| 4k–1k | 213,715 | 854,027 | 71 |
| 1d+ | 56,122 | 224,314 | 30 |

## KataGo's verdict

- **`score`** is how many points `X` is ahead after the sequence, by KataGo's estimate.
  Negative means `O` is ahead.
- **`verdict`** puts the score in words:

  | Score | Verdict | Lines |
  | --- | --- | ---: |
  | under 1 point | Even | 346 |
  | 1 to 2 | Slightly better for X / O | 60 / 103 |
  | 2 to 4 | Better for X / O | 7 / 125 |
  | 4 or more | Much better for X / O | 0 / 2 |

- **`move_loss`** is how many points the last move gave up. **`katago_next`** is the move
  KataGo would play next; `elsewhere` means it would leave the corner.
- **`depends_on_surroundings`** is true when the two test boards disagree by 3 points or
  more (27 positions). Treat those scores as unreliable.

**Mistakes.** A sequence is taken out when one side is 4 or more points behind on both test
boards. Everything that follows it is taken out with it (161 more positions). Of the 140,
130 are a single move that lost 2 points or more (`kind: mistake`), and 10 are small losses
that added up (`kind: one-sided`). They are in `data/mistakes.json` with their counts, so
you can see how common each is in each band. The two "Much better" lines above stayed in
because they reach 4 points on one board only. The scores are stored, so you can draw the
line somewhere else.

Most lines marked "Better for O" are ones where `X` played three or four stones in the
corner while `O` played elsewhere. KataGo thinks those stones would have done more
somewhere else.

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
   at least once per 10,000 corners. Its follow-ups are counted only if it was kept. This
   leaves 6,581 positions.
7. **Scoring.** KataGo 1.16.5 (network `kata1-b18c384nbt-s9996604416`, 250 visits) scored
   each position twice: with the corner in the upper right and one 4-4 stone in each other
   corner, once with two of those stones the opponent's and once with two of them `X`'s.
   Komi 6.5, Japanese rules. The score is the change in KataGo's lead from the empty
   corner, averaged over the two boards. Where a sequence has one side playing elsewhere,
   that side plays KataGo's best move outside the corner.

## Limits

- **Even to KataGo is not the same as joseki.** Nothing here was checked against a joseki
  book. A line that passed is one that is played often and does not lose 4 points.
- **The scores are small searches on a near-empty board.** 250 visits is enough to tell a
  4-point loss from an even result, not to rank two lines half a point apart. A 4-4 stone in
  each other corner decides every ladder one way, so a line that depends on a ladder or on a
  nearby stone can be scored wrongly.
- **The corner is read alone.** Stones on the sides and in other corners of the real games
  are ignored when counting.
- **Win rates are not cause.** A line with a 55% win rate may just be one that stronger
  players in the band choose.
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

**Study at your rank.** Open [`STUDY.md`](STUDY.md), or the viewer's
[Practice mode](https://jonmoses.github.io/the-great-joseki-compendium/#practice): it picks
a line at random, weighted by how often it is played in your band, and you play one side
from memory. A link such as `…/#X4-4_O3-6_X6-3` opens the viewer at that position.

**Rebuild from the dump** (about 20 GB to download; an hour to count, and about six hours
of KataGo on a laptop):

```sh
python3 scripts/corners.py ogs_games_2013_to_2021-08.json.gz corners.tsv
python3 scripts/build.py corners.tsv tree.json 1 50
python3 scripts/verify.py tree.json verify.json /path/to/katago /path/to/model.bin.gz scripts/analysis.cfg
python3 scripts/export.py tree.json verify.json .
```

The two numbers passed to `build.py` are the pruning thresholds. The bands and the date
range are constants at the top of `build.py`. The 4-point cutoff and the other export
rules are constants at the top of `export.py`. `verify.py` saves as it goes and picks up
where it stopped if you run it again.

## Licence

- **Data** (`data/`, `sgf/`): [CC0 1.0](LICENSE-DATA), public domain.
- **Code** (`scripts/`, `examples/`, `index.html`): [MIT](LICENSE-CODE).

## Thanks

To OGS for the games and for permitting the dump, to Zachary Vance for collecting it, and
to the [KataGo](https://github.com/lightvector/KataGo) project for the engine and network.
