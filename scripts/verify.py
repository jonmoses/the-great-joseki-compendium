"""Pass 4: score every position in the tree with KataGo.

usage: python3 -I verify.py TREE.json OUT.json KATAGO MODEL CONFIG [MAX_DEPTH]

Each position is set up in the upper-right corner of a 19x19 board, X as Black, in two
surroundings that are colour-swapped copies of each other (4-4 stones in the other three
corners). When a sequence has one side playing twice in a row, the other side first plays
KataGo's best move outside the corner. The output holds, per position and surrounding,
KataGo's score lead for X with the right side to move, and its preferred next move.
"""
import json
import os
import subprocess
import sys
import threading
import time

CHUNK = 60

LETTERS = 'ABCDEFGHJKLMNOPQRST'
CONTEXTS = [
    [['B', 'D4'], ['W', 'D16'], ['W', 'Q4']],
    [['W', 'D4'], ['B', 'D16'], ['B', 'Q4']],
]
REGION = [LETTERS[19 - x] + str(20 - y) for x in range(1, 11) for y in range(1, 11)]


def gtp(tok):
    x, y = (int(a) for a in tok[1:].split('-'))
    return LETTERS[19 - x] + str(20 - y)


def local(mv):
    if mv == 'pass':
        return 'pass'
    x = 19 - LETTERS.index(mv[0])
    y = 20 - int(mv[1:])
    return '%d-%d' % (x, y) if x <= 9 and y <= 9 else 'elsewhere'


class Engine:
    def __init__(self, katago, model, config):
        self.p = subprocess.Popen([katago, 'analysis', '-model', model, '-config', config],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=open(os.path.join(os.path.dirname(config), 'stderr.log'), 'a'),
                                  text=True, bufsize=1)
        self.res = {}
        self.cv = threading.Condition()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.p.stdout:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if 'id' in r:
                with self.cv:
                    self.res[r['id']] = r
                    self.cv.notify_all()

    def run(self, queries):
        """queries: {id: (ctx, moves, avoid_player or None)} -> {id: response}"""
        for qid, (ctx, moves, avoid) in queries.items():
            q = {'id': qid, 'initialStones': CONTEXTS[ctx], 'initialPlayer': 'B', 'moves': moves,
                 'rules': 'japanese', 'komi': 6.5, 'boardXSize': 19, 'boardYSize': 19}
            if avoid:
                q['avoidMoves'] = [{'player': avoid, 'moves': REGION, 'untilDepth': 1}]
            self.p.stdin.write(json.dumps(q) + '\n')
        self.p.stdin.flush()
        with self.cv:
            while not self.cv.wait_for(lambda: all(q in self.res for q in queries), timeout=20):
                if self.p.poll() is not None:
                    sys.exit('katago exited with code %s; run again to resume' % self.p.returncode)
            return {q: self.res.pop(q) for q in queries}


def main():
    tree, out, katago, model, config = sys.argv[1:6]
    max_depth = int(sys.argv[6]) if len(sys.argv) > 6 else 99
    names = list(json.load(open(tree))['nodes'])
    by_depth = {}
    for k in names:
        by_depth.setdefault(k.count(' ') + 1, []).append(k)
    state = {'root': None, 'nodes': {}, 'else': {}}
    if os.path.exists(out):
        state = json.load(open(out))
    eng = Engine(katago, model, config)
    nodes, els = state['nodes'], state['else']   # els: 'ctx|key' -> elsewhere move

    def side_to_move(moves):
        return 'B' if len(moves) % 2 == 0 else 'W'

    if state['root'] is None:
        r = eng.run({'root%d' % c: (c, [], None) for c in range(2)})
        state['root'] = [r['root%d' % c]['rootInfo']['scoreLead'] for c in range(2)]
    def level(d, todo, left):
        # which parents need an elsewhere move for the side to move
        need = {}
        plan = []
        for k in todo:
            parent = k.rsplit(' ', 1)[0] if ' ' in k else ''
            pm = [nodes[parent]['moves'][c] for c in range(2)] if parent else [[], []]
            if parent and nodes[parent].get('bad'):
                nodes[k] = {'bad': True}
                continue
            colour = 'B' if k.rsplit(' ', 1)[-1][0] == 'X' else 'W'
            tenuki = side_to_move(pm[0]) != colour
            if tenuki:
                for c in range(2):
                    if '%d|%s' % (c, parent) not in els:
                        need['e%d|%s' % (c, parent)] = (c, pm[c], side_to_move(pm[c]))
            plan.append((k, parent, pm, colour, tenuki))
        if need:
            for qid, r in eng.run(need).items():
                mv = r['moveInfos'][0]['move'] if r.get('moveInfos') else 'pass'
                els[qid[1:]] = mv
        queries = {}
        for k, parent, pm, colour, tenuki in plan:
            ml = []
            for c in range(2):
                m = list(pm[c])
                if tenuki:
                    m.append([side_to_move(m), els['%d|%s' % (c, parent)]])
                m.append([colour, gtp(k.rsplit(' ', 1)[-1])])
                ml.append(m)
                queries['%d|%s' % (c, k)] = (c, m, None)
            nodes[k] = {'moves': ml}
        res = eng.run(queries) if queries else {}
        for qid, r in res.items():
            c, k = int(qid[0]), qid[2:]
            if 'error' in r or 'rootInfo' not in r:
                nodes[k]['bad'] = True
                continue
            nodes[k].setdefault('lead', [None, None])[c] = round(r['rootInfo']['scoreLead'], 2)
            best = r['moveInfos'][0]['move'] if r.get('moveInfos') else 'pass'
            nodes[k].setdefault('best', [None, None])[c] = local(best)
        with open(out + '.tmp', 'w') as f:
            json.dump(state, f)
        os.replace(out + '.tmp', out)
        print(time.strftime('%H:%M'), 'depth', d, 'chunk of', len(todo), 'left before it', left, flush=True)

    for d in sorted(by_depth):
        if d > max_depth:
            break
        todo_all = [k for k in by_depth[d] if k not in nodes]
        for start in range(0, len(todo_all), CHUNK):
            level(d, todo_all[start:start + CHUNK], len(todo_all) - start)
    eng.p.stdin.close()


main()
