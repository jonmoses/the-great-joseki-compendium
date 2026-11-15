// Look a corner position up in data/joseki.json.
//
//   import { key, followUps } from './examples/lookup.js'
//   const book = JSON.parse(fs.readFileSync('data/joseki.json', 'utf8'))
//   const k = key([['B', 15, 3], ['W', 16, 5], ['B', 13, 2]])   // 'X4-4 O3-6 X6-3'
//   const entry = book.positions[k]

// moves: [[colour, column, row]] in play order, all in one corner of the board,
// columns and rows counted from 0 at the top left. Returns the dictionary's name.
export function key(moves, size = 19) {
  const mid = Math.floor(size / 2)
  const first = moves[0][0]
  const local = moves.map(([colour, x, y]) => {
    if (x === mid || y === mid) throw new Error('a move on a centre line belongs to no corner')
    return [colour === first ? 0 : 1, x > mid ? size - x : x + 1, y > mid ? size - y : y + 1]
  })
  const mirror = local.map(([w, x, y]) => [w, y, x])
  const less = (a, b) => {
    for (let i = 0; i < a.length; i++) {
      for (let j = 0; j < 3; j++) {
        if (a[i][j] !== b[i][j]) return a[i][j] < b[i][j]
      }
    }
    return false
  }
  const best = less(mirror, local) ? mirror : local
  return best.map(([w, x, y]) => 'XO'[w] + x + '-' + y).join(' ')
}

// The next moves after position k, with their share of the visits in one band.
export function followUps(book, k, band) {
  const i = book.meta.bands.indexOf(band)
  const here = k ? book.positions[k].count[i] : book.meta.corners[i]
  const names = k ? book.positions[k].next : book.meta.first_moves
  return names
    .map((name) => [name.split(' ').pop(), here ? book.positions[name].count[i] / here : 0])
    .sort((a, b) => b[1] - a[1])
}
