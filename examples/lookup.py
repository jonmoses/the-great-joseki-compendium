"""Look a corner position up in data/joseki.json.

    from examples.lookup import load, key
    book = load('data/joseki.json')
    k = key([('B', 15, 3), ('W', 16, 5), ('B', 13, 2)])   # 'X4-4 O3-6 X6-3'
    entry = book['positions'].get(k)
"""
import json


def load(path='data/joseki.json'):
    with open(path) as f:
        return json.load(f)


def key(moves, size=19):
    """moves: [(colour, column, row)] in play order, all in one corner of the board,
    columns and rows counted from 0 at the top left. Colour is any two distinct values.
    Returns the dictionary's name for the sequence."""
    mid = size // 2
    local = []
    first = moves[0][0]
    for colour, x, y in moves:
        if x == mid or y == mid:
            raise ValueError('a move on a centre line belongs to no corner')
        lx = (size - x) if x > mid else x + 1
        ly = (size - y) if y > mid else y + 1
        local.append((0 if colour == first else 1, lx, ly))
    mirror = [(w, y, x) for (w, x, y) in local]
    best = min(tuple(local), tuple(mirror))
    return ' '.join('XO'[w] + '%d-%d' % (x, y) for (w, x, y) in best)


def follow_ups(book, k, band):
    """The next moves after position k, with their share of the visits in one band."""
    i = book['meta']['bands'].index(band)
    here = book['positions'][k]['count'][i] if k else book['meta']['corners'][i]
    names = book['positions'][k]['next'] if k else book['meta']['first_moves']
    out = []
    for name in names:
        n = book['positions'][name]['count'][i]
        out.append((name.split(' ')[-1], n / here if here else 0.0))
    return sorted(out, key=lambda t: -t[1])
