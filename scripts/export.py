"""Pass 3: the pruned tree (build.py output) -> the published files.

usage: python3 -I export.py TREE.json REPO_DIR

Writes data/joseki.json (every position), data/lines.csv (the settled lines) and
sgf/*.sgf (one variation tree per first corner move).
"""
import csv
import json
import os
import sys

SETTLED_SHARE = 0.25     # a position is a "line" when the corner goes quiet here this often
FIRST_FRACTION = 1 / 3   # "first" band: weakest band reaching this fraction of the peak share
FAMILIES = ['4-4', '3-4', '3-3', '3-5', '4-5']


def main():
    src, repo = sys.argv[1], sys.argv[2]
    r = json.load(open(src))
    bands, corners, raw = r['bands'], r['corners'], r['nodes']
    nb = len(bands)
    kids = {}
    for k in raw:
        parent = k.rsplit(' ', 1)[0] if ' ' in k else ''
        kids.setdefault(parent, []).append(k)
    for v in kids.values():
        v.sort(key=lambda k: -sum(raw[k]['n']))

    nodes = {}
    for k, v in raw.items():
        toks = k.split(' ')
        last = toks[-1]
        x, y = (int(a) for a in last[1:].split('-'))
        per = [round(10000.0 * v['n'][i] / corners[i], 2) for i in range(nb)]
        total = sum(v['n'])
        settled = round(sum(v['end']) / total, 3)
        peak = max(range(nb), key=lambda i: per[i])
        first = next(i for i in range(nb) if per[i] >= per[peak] * FIRST_FRACTION)
        fam = toks[0][1:]
        nodes[k] = {
            'moves': k,
            'depth': len(toks),
            'family': fam if fam in FAMILIES else 'other',
            'move': {'player': last[0], 'x': x, 'y': y},
            'count': v['n'],
            'per10k': per,
            'settled_count': v['end'],
            'settled_share': settled,
            'line': len(toks) >= 3 and settled >= SETTLED_SHARE,
            'peak_band': bands[peak],
            'first_band': bands[first],
            'next': kids.get(k, []),
        }

    os.makedirs(os.path.join(repo, 'data'), exist_ok=True)
    os.makedirs(os.path.join(repo, 'sgf'), exist_ok=True)
    meta = {
        'version': 1,
        'source': 'OGS game dump 2021 (archive.org/details/ogs2021), games started 2018-01 to 2021-08',
        'bands': bands,
        'games': r['games'],
        'corners': corners,
        'min_count': r['min_count'],
        'min_per10k': r['min_share_per_10k'],
        'settled_share_for_line': SETTLED_SHARE,
        'first_band_fraction_of_peak': round(FIRST_FRACTION, 3),
        'positions': len(nodes),
        'lines': sum(1 for n in nodes.values() if n['line']),
        'first_moves': kids.get('', []),
    }
    with open(os.path.join(repo, 'data', 'joseki.json'), 'w') as f:
        json.dump({'meta': meta, 'positions': nodes}, f, separators=(',', ':'))

    lines = sorted((n for n in nodes.values() if n['line']),
                   key=lambda n: (FAMILIES.index(n['family']) if n['family'] in FAMILIES else 9,
                                  -sum(n['settled_count'])))
    with open(os.path.join(repo, 'data', 'lines.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['family', 'moves', 'stones', 'first_band', 'peak_band']
                   + ['per10k_' + b for b in bands] + ['count_' + b for b in bands]
                   + ['settled_share'])
        for n in lines:
            w.writerow([n['family'], n['moves'], n['depth'], n['first_band'], n['peak_band']]
                       + n['per10k'] + n['count'] + [n['settled_share']])

    def sgf_point(x, y):   # upper-right corner of a 19x19 board
        return chr(ord('a') + 19 - x) + chr(ord('a') + y - 1)

    def emit(k, out):
        n = nodes[k]
        m = n['move']
        c = ' | '.join('%s %s' % (bands[i], n['per10k'][i]) for i in range(nb))
        text = 'Per 10,000 corners: %s\nCorner settles here: %d%%' % (c, round(100 * n['settled_share']))
        if n['line']:
            text = 'LINE. First common at %s, most common at %s.\n' % (n['first_band'], n['peak_band']) + text
        out.append(';%s[%s]C[%s]' % ('B' if m['player'] == 'X' else 'W', sgf_point(m['x'], m['y']), text))
        ch = n['next']
        if len(ch) == 1:
            emit(ch[0], out)
        else:
            for c2 in ch:
                out.append('(')
                emit(c2, out)
                out.append(')')

    groups = {}
    for k in kids.get('', []):
        groups.setdefault(nodes[k]['family'], []).append(k)
    for fam, roots in groups.items():
        out = ['(;GM[1]FF[4]CA[UTF-8]SZ[19]GN[The Great Joseki Compendium: %s]C[First corner move %s. '
               'Black is the side that played first in the corner. Two moves in a row by one colour '
               'mean the other side played elsewhere. Numbers are occurrences per 10,000 corners '
               'in each OGS rank band.]' % (fam, fam)]
        for k in roots:
            out.append('(')
            emit(k, out)
            out.append(')')
        out.append(')')
        with open(os.path.join(repo, 'sgf', fam + '.sgf'), 'w') as f:
            f.write(''.join(out) + '\n')

    print(json.dumps(meta)[:600])
    print({fam: sum(1 for n in nodes.values() if n['family'] == fam) for fam in FAMILIES + ['other']})
    print('lines by first band', {b: sum(1 for n in lines if n['first_band'] == b) for b in bands})
    print('lines by peak band', {b: sum(1 for n in lines if n['peak_band'] == b) for b in bands})


main()
