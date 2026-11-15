"""Pass 1: OGS JSON dump (gzip, one game per line) -> one line per corner sequence.

usage: python3 -I corners.py DUMP.json.gz OUT.tsv [BOTS.txt]

Output columns: game id, year, black rank floor, white rank floor (0 = 30k), black account id,
white account id, sequence.
A sequence is the stones landing in one 9x9 quadrant during the game's first WINDOW
plies, mapped to one corner and one diagonal orientation, first mover = X, at most
MAXLEN stones. A '.' token marks where the corner went quiet for GAP plies or more
(once three stones are down); the sequence stops at the first such gap.
Banding, date and count thresholds are applied in pass 2, not here.

Bots: the dump has no bot flag. An account is dropped when its name matches BOT_WORDS
or when it is listed in BOTS.txt (account ids, one per line; built by busy.py).
"""
import gzip
import json
import sys
import time

WINDOW = 100
GAP = 8
MAXLEN = 24
BOT_WORDS = ('bot', 'gnugo', 'fuego', 'kata', 'spectral', 'zero', 'leela', 'pachi',
             'darkgo', 'elotest', 'gtp', 'engine', 'neural', 'crazystone', 'zen')


def main():
    src, out = sys.argv[1], sys.argv[2]
    bots = set()
    if len(sys.argv) > 3:
        with open(sys.argv[3]) as f:
            bots = {int(x) for x in f.read().split()}
    kept = seen = 0
    with gzip.open(src, 'rt') as f, open(out, 'w') as o:
        for line in f:
            seen += 1
            if '"width": 19' not in line and '"width":19' not in line:
                continue
            try:
                g = json.loads(line)
            except ValueError:
                continue
            if g.get('width') != 19 or g.get('height') != 19:
                continue
            if not g.get('ranked') or g.get('handicap') or g.get('phase') != 'finished':
                continue
            init = g.get('initial_state') or {}
            if init.get('black') or init.get('white') or g.get('initial_player') != 'black':
                continue
            moves = g.get('moves') or []
            if len(moves) < 30:
                continue
            pb, pw = g['players']['black'], g['players']['white']
            skip = False
            for p in (pb, pw):
                name = (p.get('username') or '').lower()
                if p.get('id') in bots or any(w in name for w in BOT_WORDS):
                    skip = True
            rb, rw = pb.get('rank'), pw.get('rank')
            if skip or rb is None or rw is None or not (0 <= rb < 40) or not (0 <= rw < 40):
                continue
            year = time.gmtime(g.get('start_time') or 0).tm_year
            seqs = [[], [], [], []]
            last = [0, 0, 0, 0]
            first = [None, None, None, None]
            closed = [False, False, False, False]
            for ply, m in enumerate(moves[:WINDOW]):
                x, y = m[0], m[1]
                if x < 0 or y < 0 or x > 18 or y > 18 or x == 9 or y == 9:
                    continue
                c = (1 if x > 9 else 0) + (2 if y > 9 else 0)
                if closed[c]:
                    continue
                s = seqs[c]
                if (len(s) >= 3 and ply - last[c] > GAP) or len(s) >= MAXLEN:
                    closed[c] = True
                    continue
                colour = ply & 1
                if first[c] is None:
                    first[c] = colour
                lx = (18 - x if c & 1 else x) + 1
                ly = (18 - y if c & 2 else y) + 1
                s.append((0 if colour == first[c] else 1, lx, ly))
                last[c] = ply
            for c in range(4):
                s = seqs[c]
                if not s:
                    continue
                a = tuple(s)
                b = tuple((w, y, x) for (w, x, y) in s)
                k = min(a, b)
                txt = ' '.join('XO'[w] + '%d-%d' % (x, y) for (w, x, y) in k)
                # '.' = went quiet (complete); no mark = cut by the stone cap or the window
                if closed[c] and len(s) < MAXLEN:
                    txt += ' .'
                o.write('%d\t%d\t%d\t%d\t%d\t%d\t%s\n' % (g.get('game_id') or 0, year, int(rb), int(rw), pb.get('id') or 0, pw.get('id') or 0, txt))
            kept += 1
            if kept % 200000 == 0:
                print(seen, kept, flush=True)
    print('lines', seen, 'games kept', kept)


main()
