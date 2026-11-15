"""Pass 2: corner sequences (corners.py output) -> the pruned tree with per-band counts.

usage: python3 -I build.py CORNERS.tsv OUT.json [MIN_SHARE_PER_10K] [MIN_COUNT]

Keeps rows from MIN_YEAR on where both players sit in the same band and neither
account is over the activity limit. Then counts prefixes level by level: a node at
depth d is counted only if its parent survived, and survives itself when in at least
one band it has MIN_COUNT occurrences and MIN_SHARE_PER_10K per 10,000 corners.
"""
import collections
import json
import sys

MIN_YEAR = 2018
BANDS = [('15k-10k', 15, 21), ('9k-5k', 21, 26), ('4k-1k', 26, 30), ('1d+', 30, 40)]
MAXDEPTH = 24


def band_of(r):
    for i, (_, lo, hi) in enumerate(BANDS):
        if lo <= r < hi:
            return i
    return -1


def main():
    src, out = sys.argv[1], sys.argv[2]
    min_share = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
    min_count = int(sys.argv[4]) if len(sys.argv) > 4 else 40

    # activity limit: distinct games per account
    per = collections.Counter()
    games = set()
    with open(src) as f:
        for line in f:
            p = line.split('\t', 6)
            gid = int(p[0])
            if gid in games:
                continue
            games.add(gid)
            per[p[4]] += 1
            per[p[5]] += 1
    limit = max(30, len(games) // 2000)
    busy = {a for a, n in per.items() if n > limit}
    total_games = len(games)
    del games, per

    rows = collections.Counter()   # (band, sequence text) -> n
    corners = [0] * len(BANDS)
    used_games = [set() for _ in BANDS]
    with open(src) as f:
        for line in f:
            gid, year, rb, rw, ib, iw, seq = line.rstrip('\n').split('\t', 6)
            if int(year) < MIN_YEAR or ib in busy or iw in busy:
                continue
            b = band_of(int(rb))
            if b < 0 or b != band_of(int(rw)):
                continue
            rows[(b, seq)] += 1
            corners[b] += 1
            used_games[b].add(int(gid))
    ngames = [len(s) for s in used_games]
    del used_games

    live = [(b, seq, n) for (b, seq), n in rows.items()]
    del rows
    nodes = {}            # prefix text -> {'n': [per band], 'end': [per band]}
    for d in range(1, MAXDEPTH + 1):
        cnt = collections.defaultdict(lambda: [0] * len(BANDS))
        end = collections.defaultdict(lambda: [0] * len(BANDS))
        keyed = []
        for b, seq, n in live:
            toks = seq.split(' ')
            quiet = toks[-1] == '.'
            body = toks[:-1] if quiet else toks
            if len(body) < d:
                continue
            key = ' '.join(body[:d])
            cnt[key][b] += n
            if quiet and len(body) == d:
                end[key][b] += n
            elif len(body) > d:
                keyed.append((key, b, seq, n))
        alive = set()
        for key, c in cnt.items():
            ok = any(c[i] >= min_count and corners[i] and 10000.0 * c[i] / corners[i] >= min_share
                     for i in range(len(BANDS)))
            if ok:
                alive.add(key)
                nodes[key] = {'n': c, 'end': end.get(key, [0] * len(BANDS))}
        live = [(b, seq, n) for (key, b, seq, n) in keyed if key in alive]
        print('depth', d, 'alive', len(alive), 'sequences left', len(live), flush=True)
        if not alive:
            break

    result = {
        'bands': [b[0] for b in BANDS], 'games': ngames, 'corners': corners,
        'total_games_read': total_games, 'activity_limit': limit, 'accounts_dropped': len(busy),
        'min_share_per_10k': min_share, 'min_count': min_count, 'nodes': nodes,
    }
    with open(out, 'w') as f:
        json.dump(result, f)
    depth = collections.Counter(len(k.split(' ')) for k in nodes)
    children = collections.Counter(' '.join(k.split(' ')[:-1]) for k in nodes)
    leaves = [k for k in nodes if k not in children]
    print(json.dumps({k: v for k, v in result.items() if k != 'nodes'}))
    print('nodes', len(nodes), 'leaves', len(leaves), 'by depth', sorted(depth.items()))


main()
