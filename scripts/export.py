"""Pass 5: the counted tree (build.py) + KataGo's scores (verify.py) -> the published files.

usage: python3 -I export.py TREE.json VERIFY.json REPO_DIR

Writes data/joseki.json (every kept position), data/lines.csv (the settled lines),
data/mistakes.json and data/mistakes.csv (common moves that leave one side 4 points or
more ahead), sgf/*.sgf and STUDY.md.
"""
import csv
import json
import os
import sys

SETTLED_SHARE = 0.25     # a position is a "line" when the corner goes quiet here this often
FIRST_FRACTION = 1 / 3   # "first" band: weakest band reaching this fraction of the peak share
MISTAKE = 4.0            # points: dropped when one side is this far ahead in both surroundings
CONTEXT_GAP = 3.0        # points: the two surroundings disagree by this much
MIN_DECIDED = 200        # games needed before a win rate is published
FAMILIES = ['4-4', '3-4', '3-3', '3-5', '4-5']
SITE = 'https://jonmoses.github.io/the-great-joseki-compendium/'


def verdict(score):
    if score is None:
        return None
    a = abs(score)
    side = 'X' if score > 0 else 'O'
    if a < 1:
        return 'Even'
    if a < 2:
        return 'Slightly better for ' + side
    if a < MISTAKE:
        return 'Better for ' + side
    return 'Much better for ' + side


def main():
    src, ver, repo = sys.argv[1], sys.argv[2], sys.argv[3]
    r = json.load(open(src))
    v = json.load(open(ver))
    bands, corners, raw = r['bands'], r['corners'], r['nodes']
    years, ycorners = r['years'], r['year_corners']
    nb = len(bands)
    vroot, vn = v['root'], v['nodes']

    def rel(k):
        """KataGo's lead for X at k minus the lead before anyone played, per surrounding."""
        e = vn.get(k)
        if not e or e.get('bad') or not e.get('lead') or None in e['lead']:
            return None
        return [e['lead'][c] - vroot[c] for c in range(2)]

    def parent_of(k):
        return k.rsplit(' ', 1)[0] if ' ' in k else ''

    order = sorted(raw, key=lambda k: k.count(' '))
    # 1. which positions are dropped, and why
    status = {}       # k -> 'ok' | 'mistake' | 'after'
    for k in order:
        p = parent_of(k)
        if p and status[p] != 'ok':
            status[k] = 'after'
            continue
        s = rel(k)
        if s and min(abs(s[0]), abs(s[1])) >= MISTAKE and (s[0] > 0) == (s[1] > 0):
            status[k] = 'mistake'
        else:
            status[k] = 'ok'

    kids = {}
    for k in order:
        if status[k] == 'ok':
            kids.setdefault(parent_of(k), []).append(k)
    for lst in kids.values():
        lst.sort(key=lambda k: -sum(raw[k]['n']))

    def describe(k):
        e = raw[k]
        toks = k.split(' ')
        last = toks[-1]
        x, y = (int(a) for a in last[1:].split('-'))
        per = [round(10000.0 * e['n'][i] / corners[i], 2) for i in range(nb)]
        settled = round(sum(e['end']) / sum(e['n']), 3)
        peak = max(range(nb), key=lambda i: per[i])
        first = next(i for i in range(nb) if per[i] >= per[peak] * FIRST_FRACTION)
        fam = toks[0][1:]
        s = rel(k)
        score = round((s[0] + s[1]) / 2, 1) if s else None
        ps = rel(parent_of(k)) if parent_of(k) else [0.0, 0.0]
        loss = None
        if s and ps:
            d = (s[0] + s[1]) / 2 - (ps[0] + ps[1]) / 2
            loss = round(max(0.0, -d if last[0] == 'X' else d), 1)
        best = None
        e2 = vn.get(k) or {}
        if e2.get('best'):
            best = sorted(set(b for b in e2['best'] if b))
        return {
            'moves': k,
            'depth': len(toks),
            'family': fam if fam in FAMILIES else 'other',
            'move': {'player': last[0], 'x': x, 'y': y},
            'count': e['n'],
            'per10k': per,
            'settled_count': e['end'],
            'settled_share': settled,
            'line': len(toks) >= 3 and settled >= SETTLED_SHARE,
            'peak_band': bands[peak],
            'first_band': bands[first],
            'per10k_by_year': [round(10000.0 * e['years'][i] / ycorners[i], 2) for i in range(len(years))],
            'x_win_rate': [round(e['xwins'][i] / e['decided'][i], 3) if e['decided'][i] >= MIN_DECIDED else None
                           for i in range(nb)],
            'score': score,
            'score_by_surrounding': [round(a, 1) for a in s] if s else None,
            'verdict': verdict(score),
            'depends_on_surroundings': bool(s) and abs(s[0] - s[1]) >= CONTEXT_GAP,
            'move_loss': loss,
            'katago_next': best,
        }

    nodes = {}
    mistakes = {}
    for k in order:
        if status[k] == 'ok':
            n = describe(k)
            n['next'] = kids.get(k, [])
            nodes[k] = n
        elif status[k] == 'mistake':
            n = describe(k)
            p = parent_of(k)
            n['after'] = p
            n['better'] = (vn.get(p) or {}).get('best') and sorted(set(vn[p]['best']))
            # the side that is behind; 'mistake' when the last move itself lost 2+ points,
            # 'one-sided' when smaller losses added up to the cutoff
            n['by'] = 'O' if n['score'] > 0 else 'X'
            n['kind'] = ('mistake' if n['move']['player'] == n['by'] and (n['move_loss'] or 0) >= 2.0
                         else 'one-sided')
            for drop in ('line', 'settled_count', 'settled_share', 'katago_next', 'verdict'):
                n.pop(drop)
            mistakes[k] = n
    for k, n in nodes.items():
        n['mistakes'] = sorted((m for m in mistakes if mistakes[m]['after'] == k),
                               key=lambda m: -sum(mistakes[m]['count']))
    root_mistakes = [m for m in mistakes if mistakes[m]['after'] == '']

    os.makedirs(os.path.join(repo, 'data'), exist_ok=True)
    os.makedirs(os.path.join(repo, 'sgf'), exist_ok=True)
    lines = sorted((n for n in nodes.values() if n['line']),
                   key=lambda n: (FAMILIES.index(n['family']) if n['family'] in FAMILIES else 9,
                                  -sum(n['settled_count'])))
    unscored = sum(1 for n in nodes.values() if n['score'] is None)
    meta = {
        'version': 2,
        'source': 'OGS game dump 2021 (archive.org/details/ogs2021), games started 2018-01 to 2021-08',
        'bands': bands, 'games': r['games'], 'corners': corners,
        'years': years, 'year_corners': ycorners,
        'min_count': r['min_count'], 'min_per10k': r['min_share_per_10k'],
        'settled_share_for_line': SETTLED_SHARE,
        'first_band_fraction_of_peak': round(FIRST_FRACTION, 3),
        'mistake_points': MISTAKE, 'surroundings_gap_points': CONTEXT_GAP,
        'min_decided_for_win_rate': MIN_DECIDED,
        'positions': len(nodes), 'lines': len(lines), 'mistakes': len(mistakes),
        'positions_after_a_mistake_removed': sum(1 for s in status.values() if s == 'after'),
        'unscored_positions': unscored,
        'first_moves': kids.get('', []), 'first_move_mistakes': root_mistakes,
    }
    with open(os.path.join(repo, 'data', 'joseki.json'), 'w') as f:
        json.dump({'meta': meta, 'positions': nodes}, f, separators=(',', ':'))
    with open(os.path.join(repo, 'data', 'mistakes.json'), 'w') as f:
        json.dump({'meta': {k: meta[k] for k in ('version', 'source', 'bands', 'corners', 'mistake_points')},
                   'mistakes': mistakes}, f, separators=(',', ':'))

    with open(os.path.join(repo, 'data', 'lines.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['family', 'moves', 'stones', 'first_band', 'peak_band', 'verdict', 'score_for_x',
                    'depends_on_surroundings']
                   + ['per10k_' + b for b in bands] + ['count_' + b for b in bands]
                   + ['x_win_rate_' + b for b in bands] + ['per10k_' + str(y) for y in years]
                   + ['settled_share'])
        for n in lines:
            w.writerow([n['family'], n['moves'], n['depth'], n['first_band'], n['peak_band'],
                        n['verdict'], n['score'], n['depends_on_surroundings']]
                       + n['per10k'] + n['count'] + n['x_win_rate'] + n['per10k_by_year']
                       + [n['settled_share']])
    mlist = sorted(mistakes.values(), key=lambda n: -sum(n['count']))
    with open(os.path.join(repo, 'data', 'mistakes.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['after', 'mistake', 'kind', 'side_behind', 'points_lost_by_this_move', 'score_for_x', 'katago_prefers',
                    'peak_band'] + ['per10k_' + b for b in bands] + ['count_' + b for b in bands])
        for n in mlist:
            w.writerow([n['after'], n['moves'].rsplit(' ', 1)[-1], n['kind'], n['by'], n['move_loss'], n['score'],
                        ' or '.join(n['better'] or []), n['peak_band']] + n['per10k'] + n['count'])

    def sgf_point(x, y):   # upper-right corner of a 19x19 board
        return chr(ord('a') + 19 - x) + chr(ord('a') + y - 1)

    def colour(v):
        return v.replace('for X', 'for Black').replace('for O', 'for White') if v else 'Not scored'

    def emit(k, out):
        n = nodes[k]
        m = n['move']
        c = ' | '.join('%s %s' % (bands[i], n['per10k'][i]) for i in range(nb))
        text = 'Per 10,000 corners: %s\nCorner settles here: %d%%\nKataGo: %s' % (
            c, round(100 * n['settled_share']), colour(n['verdict']))
        if n['score'] is not None:
            text += ' (%+.1f for Black)' % n['score']
        if n['depends_on_surroundings']:
            text += '. Depends on the rest of the board'
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
               'in each OGS rank band. KataGo scores are points, positive for Black.]' % (fam, fam)]
        for k in roots:
            out.append('(')
            emit(k, out)
            out.append(')')
        out.append(')')
        with open(os.path.join(repo, 'sgf', fam + '.sgf'), 'w') as f:
            f.write(''.join(out) + '\n')

    # STUDY.md: what to learn at each rank
    def link(k):
        return '[`%s`](%s#%s)' % (k, SITE, k.replace(' ', '_'))

    md = ['# Study lists by rank', '',
          'Generated from the data. For each band: the settled lines played most often there, and the '
          'most common mistakes. Every sequence links to the viewer.', '',
          '`X` is the side that played first in the corner. Scores are KataGo\'s, in points, '
          'positive for `X`. "Once in N games" counts all four corners.', '']
    for i, b in enumerate(bands):
        md += ['## ' + b, '', '### Lines to know', '',
               '| # | Line | How often | KataGo | New here |', '| ---: | --- | --- | --- | --- |']
        top = sorted(lines, key=lambda n: -n['settled_count'][i])[:30]
        for j, n in enumerate(top):
            every = corners[i] / 4.0 / max(1, n['count'][i])
            md.append('| %d | %s | once in %d games | %s | %s |' % (
                j + 1, link(n['moves']), round(every), n['verdict'] or 'not scored',
                'yes' if n['first_band'] == b and i > 0 else ''))
        md += ['', '### Common mistakes', '',
               '| # | After | Mistake | Costs | KataGo prefers | How often |',
               '| ---: | --- | --- | ---: | --- | --- |']
        topm = sorted((n for n in mlist if n['kind'] == 'mistake'), key=lambda n: -n['count'][i])[:15]
        for j, n in enumerate(topm):
            every = corners[i] / 4.0 / max(1, n['count'][i])
            md.append('| %d | %s | `%s` | %s | %s | once in %d games |' % (
                j + 1, link(n['after']) if n['after'] else 'empty corner', n['moves'].rsplit(' ', 1)[-1],
                n['move_loss'], ' or '.join(n['better'] or []) or '', round(every)))
        md.append('')
    with open(os.path.join(repo, 'STUDY.md'), 'w') as f:
        f.write('\n'.join(md))

    tiers = {}
    for n in lines:
        tiers[n['verdict']] = tiers.get(n['verdict'], 0) + 1
    print(json.dumps({k: meta[k] for k in ('positions', 'lines', 'mistakes',
                                           'positions_after_a_mistake_removed', 'unscored_positions')}))
    print('line verdicts', tiers)
    print('lines that depend on surroundings', sum(1 for n in lines if n['depends_on_surroundings']))


main()
