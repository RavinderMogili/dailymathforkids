import datetime
import hashlib
import html
import math
import random
import re


def _grid(rows, cols, label, shaded=False, marks=None, caption=''):
    cells = []
    marks = marks or {}
    for y in range(rows):
        for x in range(cols):
            fill = '#cbd5e1' if shaded and (x + y) % 2 == 0 else '#ffffff'
            if (x, y) in marks:
                fill = marks[(x, y)]
            cells.append(f'<rect x="{10 + x * 32}" y="{10 + y * 32}" width="32" height="32" fill="{fill}" stroke="#334155"/>')
    text = f'<text x="10" y="{rows * 32 + 34}" font-size="14" fill="#334155">{html.escape(caption)}</text>' if caption else ''
    height = rows * 32 + (42 if caption else 20)
    return (f'<svg class="challenge-diagram" role="img" aria-label="{html.escape(label, quote=True)}" '
            f'viewBox="0 0 {cols * 32 + 20} {height}" '
            'style="display:block;width:100%;max-width:360px;height:auto;margin:12px 0">'
            + ''.join(cells) + text + '</svg>')


def _svg(label, w, h, inner):
    return (f'<svg class="challenge-diagram" role="img" aria-label="{html.escape(label, quote=True)}" '
            f'viewBox="0 0 {w} {h}" '
            'style="display:block;width:100%;max-width:360px;height:auto;margin:12px 0">'
            + inner + '</svg>')


def _number_line(lo, hi, segments, arrow_idx, label, tick_labels):
    """Number line lo..hi divided into `segments` parts; arrow above tick arrow_idx.
    tick_labels: set of tick indices whose value is printed (endpoints at least)."""
    w = 340
    x0, y = 30, 56
    parts = [f'<line x1="{x0 - 12}" y1="{y}" x2="{x0 + w + 12}" y2="{y}" stroke="#334155" stroke-width="2"/>',
             f'<polygon points="{x0 - 14},{y} {x0 - 6},{y - 5} {x0 - 6},{y + 5}" fill="#334155"/>',
             f'<polygon points="{x0 + w + 14},{y} {x0 + w + 6},{y - 5} {x0 + w + 6},{y + 5}" fill="#334155"/>']
    for i in range(segments + 1):
        x = x0 + w * i / segments
        parts.append(f'<line x1="{x:.1f}" y1="{y - 6}" x2="{x:.1f}" y2="{y + 6}" stroke="#334155" stroke-width="1.5"/>')
        if i in tick_labels:
            v = lo + (hi - lo) * i / segments
            txt = f'{v:g}' if abs(v - round(v)) < 1e-9 else f'{v:.1f}'
            parts.append(f'<text x="{x:.1f}" y="{y + 22}" font-size="13" fill="#334155" text-anchor="middle">{txt}</text>')
    ax = x0 + w * arrow_idx / segments
    parts.append(f'<line x1="{ax:.1f}" y1="{y - 34}" x2="{ax:.1f}" y2="{y - 10}" stroke="#e11d48" stroke-width="2"/>')
    parts.append(f'<polygon points="{ax - 6:.1f},{y - 10} {ax + 6:.1f},{y - 10} {ax:.1f},{y - 3}" fill="#e11d48"/>')
    return _svg(label, x0 + w + 46, y + 30, ''.join(parts))


def _tenth_frame(shaded, label):
    """2x5 frame worth 1 whole; `shaded` cells filled left-to-right."""
    parts = []
    for i in range(10):
        x, y = 10 + (i % 5) * 56, 10 + (i // 5) * 48
        fill = '#94a3b8' if i < shaded else '#ffffff'
        parts.append(f'<rect x="{x}" y="{y}" width="56" height="48" fill="{fill}" stroke="#334155" stroke-width="1.5"/>')
    return _svg(label, 300, 116, ''.join(parts))


def _triangle(sides, label):
    """Triangle (drawn to scale via cosine rule) with side labels a,b,c in cm."""
    a, b, c = sides  # c = base length
    Ax, Ay = 40.0, 130.0
    Bx, By = Ax + c * 18.0, Ay
    cos_a = (b * b + c * c - a * a) / (2 * b * c)
    cos_a = max(-1.0, min(1.0, cos_a))
    sin_a = math.sqrt(max(0.0, 1 - cos_a * cos_a))
    Cx, Cy = Ax + b * 18.0 * cos_a, Ay - b * 18.0 * sin_a
    parts = [f'<polygon points="{Ax:.0f},{Ay:.0f} {Bx:.0f},{By:.0f} {Cx:.0f},{Cy:.0f}" '
             'fill="#e2e8f0" stroke="#334155" stroke-width="2"/>']
    for (x1, y1, x2, y2, s, dx, dy) in [
            (Ax, Ay, Bx, By, c, 0, 16), (Bx, By, Cx, Cy, a, 14, 4), (Ax, Ay, Cx, Cy, b, -22, 4)]:
        mx, my = (x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy
        parts.append(f'<text x="{mx:.0f}" y="{my:.0f}" font-size="13" fill="#334155" text-anchor="middle">{s} cm</text>')
    right = abs(a * a - (b * b + c * c)) < 1e-9 or abs(b * b - (a * a + c * c)) < 1e-9 or abs(c * c - (a * a + b * b)) < 1e-9
    if right:  # small square at the right-angle vertex (A when c^2+b^2=a^2 etc.)
        vx, vy = (Ax, Ay) if abs(a * a - (b * b + c * c)) < 1e-9 else ((Bx, By) if abs(b * b - (a * a + c * c)) < 1e-9 else (Cx, Cy))
        parts.append(f'<rect x="{vx - 7:.0f}" y="{vy - 14:.0f}" width="12" height="12" fill="none" stroke="#334155"/>')
    return _svg(label, 300, 150, ''.join(parts))


def _data_table(headers, rows, label):
    colw, rowh = 110, 30
    w, h = len(headers) * colw + 20, (len(rows) + 1) * rowh + 20
    parts = [f'<rect x="10" y="10" width="{w - 20}" height="{rowh}" fill="#e2e8f0" stroke="#334155"/>']
    for i, hd in enumerate(headers):
        parts.append(f'<text x="{10 + i * colw + colw / 2}" y="{10 + rowh / 2 + 5}" font-size="13" font-weight="bold" '
                     f'fill="#334155" text-anchor="middle">{html.escape(str(hd))}</text>')
        parts.append(f'<line x1="{10 + i * colw}" y1="10" x2="{10 + i * colw}" y2="{h - 10}" stroke="#334155"/>')
    parts.append(f'<line x1="{10 + len(headers) * colw}" y1="10" x2="{10 + len(headers) * colw}" y2="{h - 10}" stroke="#334155"/>')
    for r, row in enumerate(rows):
        y = 10 + (r + 1) * rowh
        parts.append(f'<line x1="10" y1="{y}" x2="{w - 10}" y2="{y}" stroke="#334155"/>')
        for i, cell in enumerate(row):
            parts.append(f'<text x="{10 + i * colw + colw / 2}" y="{y + rowh / 2 + 5}" font-size="13" fill="#334155" '
                         f'text-anchor="middle">{html.escape(str(cell))}</text>')
    parts.append(f'<line x1="10" y1="{h - 10}" x2="{w - 10}" y2="{h - 10}" stroke="#334155"/>')
    return _svg(label, w, h, ''.join(parts))


def _bar_graph(items, label, ymax=None):
    bw, gap, h_max, base = 44, 30, 130, 160
    mx = ymax or max(v for _, v in items)
    parts = [f'<line x1="20" y1="20" x2="20" y2="{base}" stroke="#334155"/>',
             f'<line x1="20" y1="{base}" x2="{30 + len(items) * (bw + gap)}" y2="{base}" stroke="#334155"/>']
    for frac in (0, 0.5, 1):
        vy = base - h_max * frac
        parts.append(f'<line x1="14" y1="{vy:.0f}" x2="20" y2="{vy:.0f}" stroke="#334155"/>')
        parts.append(f'<text x="10" y="{vy + 4:.0f}" font-size="11" fill="#334155" text-anchor="middle">{int(mx * frac)}</text>')
    x = 40
    for name, v in items:
        bh = h_max * v / mx
        parts.append(f'<rect x="{x}" y="{base - bh:.0f}" width="{bw}" height="{bh:.0f}" fill="#94a3b8" stroke="#334155"/>')
        parts.append(f'<text x="{x + bw / 2}" y="{base - bh - 5:.0f}" font-size="12" fill="#334155" text-anchor="middle">{v}</text>')
        parts.append(f'<text x="{x + bw / 2}" y="{base + 16}" font-size="12" fill="#334155" text-anchor="middle">{html.escape(name)}</text>')
        x += bw + gap
    return _svg(label, x + 10, base + 24, ''.join(parts))


def _wheel(shaded, total, label):
    """Single spinner: circle split into `total` equal sectors, first `shaded` grey."""
    cx, cy, r = 70, 68, 48
    parts = []
    for i in range(total):
        a0 = -math.pi / 2 + 2 * math.pi * i / total
        a1 = a0 + 2 * math.pi / total
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        fill = '#94a3b8' if i < shaded else '#ffffff'
        parts.append(f'<path d="M {cx},{cy} L {x0:.1f},{y0:.1f} A {r},{r} 0 0 1 {x1:.1f},{y1:.1f} Z" '
                     f'fill="{fill}" stroke="#334155" stroke-width="1.4"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#334155" stroke-width="2"/>')
    parts.append(f'<polygon points="{cx},{cy - r - 2} {cx - 7},{cy - r - 16} {cx + 7},{cy - r - 16}" fill="#e11d48"/>')
    return _svg(label, 2 * cx, 2 * cy + 12, ''.join(parts))


def _wheels(specs, label):
    """Row of small wheels labeled A, B, C, ... ; specs = [(shaded, total), ...]."""
    r, cy = 34, 52
    parts = []
    for i, (sh, tot) in enumerate(specs):
        cx = 50 + i * 110
        for k in range(tot):
            a0 = -math.pi / 2 + 2 * math.pi * k / tot
            a1 = a0 + 2 * math.pi / tot
            x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
            x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
            fill = '#94a3b8' if k < sh else '#ffffff'
            parts.append(f'<path d="M {cx},{cy} L {x0:.1f},{y0:.1f} A {r},{r} 0 0 1 {x1:.1f},{y1:.1f} Z" '
                         f'fill="{fill}" stroke="#334155" stroke-width="1.2"/>')
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#334155" stroke-width="2"/>')
        parts.append(f'<text x="{cx}" y="{cy + r + 20}" font-size="14" font-weight="bold" fill="#334155" '
                     f'text-anchor="middle">{chr(65 + i)}</text>')
    return _svg(label, 50 + (len(specs) - 1) * 110 + 50, cy + r + 30, ''.join(parts))


def _hexagon(shaded, label):
    """Regular hexagon split into 6 triangles through the centre; first `shaded` grey."""
    cx, cy, r = 75, 64, 52
    verts = [(cx + r * math.cos(-math.pi / 2 + math.pi * i / 3),
              cy + r * math.sin(-math.pi / 2 + math.pi * i / 3)) for i in range(6)]
    parts = []
    for i in range(6):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % 6]
        fill = '#94a3b8' if i < shaded else '#ffffff'
        parts.append(f'<polygon points="{cx},{cy} {x0:.1f},{y0:.1f} {x1:.1f},{y1:.1f}" '
                     f'fill="{fill}" stroke="#334155" stroke-width="1.5"/>')
    parts.append('<polygon points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in verts)
                 + '" fill="none" stroke="#334155" stroke-width="2"/>')
    return _svg(label, 150, 130, ''.join(parts))


def _yarn_balls(d1, d2, label):
    """Two circles side by side labeled by diameter (yarn ball before/after)."""
    r1, r2 = 42, 21
    parts = [f'<circle cx="56" cy="62" r="{r1}" fill="#e2e8f0" stroke="#334155" stroke-width="2"/>',
             f'<text x="56" y="{62 + r1 + 18}" font-size="13" fill="#334155" text-anchor="middle">{d1} cm</text>',
             f'<circle cx="176" cy="{62 + r1 - r2}" r="{r2}" fill="#e2e8f0" stroke="#334155" stroke-width="2"/>',
             f'<text x="176" y="{62 + r1 + 18}" font-size="13" fill="#334155" text-anchor="middle">{d2} cm</text>']
    return _svg(label, 240, 132, ''.join(parts))


def _choice_values(answer, rng):
    answer = str(answer)
    if answer.isdigit():
        value = int(answer)
        values = {value, value + 1, value + 2, max(0, value - 1)}
        while len(values) < 4:
            values.add(value + len(values) + 2)
        choices = [str(v) for v in values]
    elif re.fullmatch(r'\d+/\d+', answer):
        num, den = (int(x) for x in answer.split('/'))
        cands = [f'{den - num}/{den}' if den - num else None,
                 f'{num}/{num}' if num != den else None,
                 f'{den}/{num}',
                 f'{max(1, num - 1)}/{den}' if num != 1 else f'{num}/{den + 1}',
                 f'{num + 1}/{den}']
        choices = [answer]
        for c in cands:
            if c and c != answer and len(choices) < 4:
                choices.append(c)
        extra = 1
        while len(choices) < 4:
            c = f'{num + extra}/{den + extra}'
            if c != answer:
                choices.append(c)
            extra += 1
    elif re.fullmatch(r'-?\d+\.\d+', answer):
        v = float(answer)
        dec = len(answer.split('.')[1])
        step = 10 ** -dec
        cands = [v + step, v - step if v - step > 0 else v + 3 * step,
                 v + 2 * step, v + 4 * step]
        choices = [answer]
        for c in cands:
            s = f'{c:.{dec}f}'
            if s != answer and s not in choices and len(choices) < 4:
                choices.append(s)
    else:
        choices = [answer]
        pool = ['Yes / oui', 'No / non', 'Left / gauche', 'Right / droite', 'A', 'B', 'C']
        for item in pool:
            if item != answer and len(choices) < 4:
                choices.append(item)
    rng.shuffle(choices)
    return choices


def _text_choices(answer, pool, rng):
    """For text answers (e.g. triangle types): answer + 3 distractors from pool."""
    others = [p for p in pool if p != answer]
    rng.shuffle(others)
    choices = others[:3] + [answer]
    rng.shuffle(choices)
    return choices


def make_challenge(grade, day, slot=0):
    if grade not in range(1, 13):
        raise ValueError('grade must be between 1 and 12')
    if slot not in (0, 1):
        raise ValueError('slot must be 0 or 1')
    date = datetime.date.fromisoformat(str(day))
    seed = hashlib.sha256(f'{date.isoformat()}:{grade}:{slot}:challenge-v2'.encode()).hexdigest()
    rng = random.Random(seed)
    n = rng.randint(3, 5)
    choices = None

    if grade <= 2:
        if slot == 0:
            cols = grade + 4
            highlighted = {i: rng.randint(0, cols - 1) for i in range(2)}
            en = f'Look at the two grey squares. Counting from the left, what is their total position? For example, the first square has position 1.'
            fr = 'Regarde les deux cases grises. En comptant à partir de la gauche, quelle est la somme de leurs positions ? Par exemple, la première case a la position 1.'
            answer = sum(v + 1 for v in highlighted.values())
            hint = 'Write the position under each grey square, then add.'
            steps = [f'The positions are {min(v + 1 for v in highlighted.values())} and {max(v + 1 for v in highlighted.values())}.', f'Add them to get {answer}.']
            marks = {(v, i): '#94a3b8' for i, v in enumerate(highlighted.values())}
            diagram = _grid(2, cols, en, marks=marks)
        else:
            rows = 2 + (grade - 1)
            en = f'Count the white squares in this {rows} by {n + 2} grid.'
            fr = f'Compte les cases blanches dans cette grille de {rows} sur {n + 2}.'
            answer = rows * (n + 2)
            hint = 'Count one full row, then use equal groups.'
            steps = [f'Each row has {n + 2} squares.', f'{rows} rows of {n + 2} makes {answer}.']
            diagram = _grid(rows, n + 2, en)
    elif grade <= 4:
        if slot == 0:
            variant = rng.randint(0, 3)
            if variant == 0:
                cols = grade
                en = f'How many rectangles of any size can be traced along the lines of this 2 by {cols} grid? Count squares as rectangles too.'
                fr = f'Combien de rectangles de toutes tailles peut-on tracer sur les lignes de cette grille de 2 sur {cols} ? Compte aussi les carrés.'
                answer = 3 * math.comb(cols + 1, 2)
                hint = 'Choose a left/right pair of vertical lines, then choose a top/bottom pair.'
                steps = [f'There are {math.comb(cols + 1, 2)} pairs of vertical grid lines.', 'There are 3 pairs of horizontal grid lines.', f'Multiply to get {answer}.']
                diagram = _grid(2, cols, en)
            elif variant == 1:
                segments = rng.choice([4, 5, 8])
                hi = rng.choice([400, 600, 800, 1000, 1200])
                while hi % segments:
                    hi += segments - hi % segments
                idx = rng.randint(1, segments - 1)
                step = hi // segments
                answer = idx * step
                en = 'What number is the arrow pointing to on this number line?'
                fr = 'Vers quel nombre la flèche pointe-t-elle sur cette droite numérique ?'
                hint = f'Find what each gap is worth first.'
                steps = [f'The line from 0 to {hi} is split into {segments} equal parts.', f'Each part is {hi} ÷ {segments} = {step}.', f'The arrow is at mark {idx}: {idx} × {step} = {answer}.']
                diagram = _number_line(0, hi, segments, idx, en, tick_labels={0, segments})
            elif variant == 2:
                names = ['Liam', 'Emma', 'Noah', 'Ava']
                rng.shuffle(names)
                vals = [rng.randint(4, 12) * 5 for _ in range(4)]
                items = list(zip(names, vals))
                en = 'How many more points did the top scorer get than the lowest scorer?'
                fr = 'Combien de points de plus le meilleur joueur a-t-il marqués que le dernier ?'
                answer = max(vals) - min(vals)
                hint = 'Find the tallest bar and the shortest bar.'
                steps = [f'Top scorer: {max(vals)} points.', f'Lowest: {min(vals)} points.', f'Difference: {max(vals)} − {min(vals)} = {answer}.']
                diagram = _bar_graph(items, en)
            else:
                vals = [rng.randint(2, 9) * 1000 + rng.randint(1, 9) * 100 for _ in range(2)]
                total_needed = vals[0] + vals[1]
                en = 'Using the table, how many tickets were sold in total on both days?'
                fr = 'En utilisant le tableau, combien de billets ont été vendus au total les deux jours ?'
                answer = total_needed
                hint = 'Add the two numbers in the table.'
                steps = [f'Saturday: {vals[0]:,} tickets.', f'Sunday: {vals[1]:,} tickets.', f'Total: {vals[0]:,} + {vals[1]:,} = {answer:,}.']
                diagram = _data_table(['Day', 'Tickets'], [['Saturday', f'{vals[0]:,}'], ['Sunday', f'{vals[1]:,}']], en)
        else:
            variant = rng.randint(0, 2)
            if variant == 0:
                rows = grade - 1
                shaded_count = rng.randint(rows + 1, rows * 2)
                marks = {}
                for i in range(shaded_count):
                    marks[(i % (rows + 1), i // (rows + 1))] = '#94a3b8'
                en = f'In this {rows} by {rows + 1} grid, how many squares are not shaded?'
                fr = f'Dans cette grille de {rows} sur {rows + 1}, combien de cases ne sont pas grisées ?'
                answer = rows * (rows + 1) - shaded_count
                hint = 'Count all squares first, then remove the shaded squares.'
                steps = [f'The whole grid has {rows} times {rows + 1}, or {rows * (rows + 1)}, squares.', f'Remove {shaded_count} shaded squares to get {answer}.']
                diagram = _grid(rows, rows + 1, en, marks=marks)
            elif variant == 1:
                shaded = rng.randint(2, 9)
                if grade == 3:
                    en = 'The ten-frame shows one whole split into 10 equal parts. What fraction is shaded?'
                    fr = 'Le cadre à dix montre un entier divisé en 10 parties égales. Quelle fraction est grisée ?'
                    answer = f'{shaded}/10'
                    hint = 'Count the shaded parts out of all 10 parts.'
                    steps = [f'There are {shaded} shaded parts.', f'Out of 10 parts, the fraction is {answer}.']
                else:
                    en = 'This ten-frame is worth 1 whole. What decimal is represented?'
                    fr = 'Ce cadre à dix vaut 1 entier. Quelle décimale est représentée ?'
                    answer = f'0.{shaded}'
                    hint = 'Each part is worth one tenth, or 0.1.'
                    steps = [f'Each part = 0.1.', f'{shaded} shaded parts = {shaded} × 0.1 = {answer}.']
                diagram = _tenth_frame(shaded, en)
            else:
                triples = [(3, 4, 5), (5, 5, 6), (4, 5, 6), (6, 8, 10), (5, 6, 7)]
                a, b, c = rng.choice(triples)
                en = 'Find the perimeter of this triangle.'
                fr = 'Trouve le périmètre de ce triangle.'
                answer = a + b + c
                hint = 'Add all three side lengths.'
                steps = [f'Perimeter = {a} + {b} + {c} = {answer} cm.']
                diagram = _triangle((a, b, c), en)
    elif grade <= 6:
        if slot == 0:
            variant = rng.randint(0, 3)
            if variant == 0:
                en = f'On this 2 by {n} grid, how many shortest routes go from the bottom-left corner to the top-right corner using only right and up moves?'
                fr = f'Sur cette grille de 2 sur {n}, combien de trajets les plus courts vont du coin inférieur gauche au coin supérieur droit, seulement vers la droite ou vers le haut ?'
                answer = math.comb(n + 2, 2)
                hint = 'Choose which two moves in the route go up.'
                steps = [f'Each shortest route has {n} right moves and 2 up moves.', f'Choose the two up positions to get C({n + 2}, 2) = {answer}.']
                diagram = _grid(2, n, en)
            elif variant == 1:
                idx = rng.randint(1, 9)
                en = 'What decimal is the arrow pointing to on this number line?'
                fr = 'Vers quelle décimale la flèche pointe-t-elle sur cette droite numérique ?'
                answer = f'0.{idx}'
                hint = 'Count how many equal parts the line is split into.'
                steps = [f'The line from 0 to 1 is split into 10 equal parts.', f'Each part is 0.1.', f'The arrow is at mark {idx}: {idx} × 0.1 = {answer}.']
                diagram = _number_line(0, 1, 10, idx, en, tick_labels={0, 10})
            elif variant == 2:
                triples = [(6, 8, 10), (5, 12, 13), (7, 8, 9), (9, 10, 11), (8, 8, 6)]
                a, b, c = rng.choice(triples)
                en = 'Find the perimeter of this triangle.'
                fr = 'Trouve le périmètre de ce triangle.'
                answer = a + b + c
                hint = 'Add all three side lengths.'
                steps = [f'Perimeter = {a} + {b} + {c} = {answer} cm.']
                diagram = _triangle((a, b, c), en)
            else:
                names = ['Mia', 'Lucas', 'Sofia', 'Ethan']
                rng.shuffle(names)
                vals = [rng.randint(3, 10) * 10 for _ in range(4)]
                items = list(zip(names, vals))
                order = sorted(items, key=lambda kv: kv[1])
                lo_name, lo_v = order[0]
                hi_name, hi_v = order[-1]
                en = f'How many more books did {hi_name} read than {lo_name}?'
                fr = f'Combien de livres de plus {hi_name} a-t-il lus que {lo_name} ?'
                answer = hi_v - lo_v
                hint = 'Compare the tallest and shortest bars.'
                steps = [f'{hi_name}: {hi_v} books.', f'{lo_name}: {lo_v} books.', f'Difference: {hi_v} − {lo_v} = {answer}.']
                diagram = _bar_graph(items, en)
        else:
            variant = rng.randint(0, 2)
            if variant == 0:
                rows, cols = 3, n + 1
                numerator = rng.randint(2, cols)
                marks = {}
                for i in range(numerator * rows):
                    marks[(i % cols, i // cols)] = '#94a3b8'
                en = f'Each column of this grid is one group. What fraction of the grid is shaded?'
                fr = 'Chaque colonne de cette grille forme un groupe. Quelle fraction de la grille est grisée ?'
                answer = f'{numerator}/{cols}'
                hint = 'Count complete shaded columns out of all columns.'
                steps = [f'There are {numerator} shaded columns.', f'There are {cols} columns altogether, so the fraction is {answer}.']
                diagram = _grid(rows, cols, en, marks=marks)
            elif variant == 1:
                shaded = rng.randint(2, 9)
                en = 'This ten-frame is worth 1 whole. What decimal is represented?'
                fr = 'Ce cadre à dix vaut 1 entier. Quelle décimale est représentée ?'
                answer = f'0.{shaded}'
                hint = 'Each part is worth one tenth, or 0.1.'
                steps = [f'Each part = 0.1.', f'{shaded} shaded parts = {shaded} × 0.1 = {answer}.']
                diagram = _tenth_frame(shaded, en)
            else:
                vals = [rng.randint(20, 90) * 100 for _ in range(3)]
                en = 'Using the table, how many pumpkins were harvested in total this year?'
                fr = 'En utilisant le tableau, combien de citrouilles ont été récoltées au total cette année ?'
                answer = sum(vals)
                hint = 'Add the three numbers in the table.'
                steps = [f'August: {vals[0]:,}.', f'September: {vals[1]:,}.', f'October: {vals[2]:,}.', f'Total: {vals[0]:,} + {vals[1]:,} + {vals[2]:,} = {answer:,}.']
                diagram = _data_table(['Month', 'Pumpkins'], [['August', f'{vals[0]:,}'], ['September', f'{vals[1]:,}'], ['October', f'{vals[2]:,}']], en)
    elif grade <= 8:
        if slot == 0:
            variant = rng.randint(0, 1)
            if variant == 0:
                moves = 2 * n + 1
                en = f'A counter starts on a grey square. Each move goes to a square sharing a side. After {moves} moves, what type of square must it occupy?'
                fr = f'Un pion part d’une case grise. Chaque déplacement mène à une case voisine par un côté. Après {moves} déplacements, sur quel type de case est-il forcément ?'
                answer = 'White / blanche'
                hint = 'Track the colour after one move, then after two moves.'
                steps = ['Every move changes the colour.', f'{moves} is odd, so the final colour is the opposite of the starting colour.']
                diagram = _grid(4, 4, en, shaded=True)
            else:
                type_triples = {
                    'scalene / scalène': [(4, 5, 6), (5, 6, 8), (7, 9, 11)],
                    'isosceles / isocèle': [(6, 6, 4), (8, 8, 5), (7, 7, 9)],
                    'equilateral / équilatéral': [(6, 6, 6), (8, 8, 8)],
                    'right-angled / rectangle': [(3, 4, 5), (6, 8, 10), (5, 12, 13)],
                }
                answer = rng.choice(list(type_triples))
                sides = rng.choice(type_triples[answer])
                en = 'Classify this triangle by its sides (and angles).'
                fr = 'Classe ce triangle selon ses côtés (et ses angles).'
                pool = list(type_triples)
                choices = _text_choices(answer, pool, rng)
                hint = 'Compare the three side lengths; look for a right-angle mark too.'
                s = sorted(sides)
                kind = ('all three sides equal' if len(set(sides)) == 1
                        else 'two sides equal' if len(set(sides)) == 2
                        else f'{s[0]}² + {s[1]}² = {s[0]**2 + s[1]**2} = {s[2]}² (right angle)' if s[0]**2 + s[1]**2 == s[2]**2
                        else 'all three sides different')
                steps = [f'The sides are {sides[0]}, {sides[1]} and {sides[2]} cm.', f'Check: {kind}.', f'So the triangle is {answer.split(" /")[0]}.']
                diagram = _triangle(sides, en)
        else:
            variant = rng.randint(0, 1)
            if variant == 0:
                seats = n + 4
                en = f'The row shows {seats} seats. In how many ways can you choose two seats that do not share a side?'
                fr = f'La rangée montre {seats} places. De combien de façons peut-on choisir deux places qui ne se touchent pas par un côté ?'
                answer = math.comb(seats, 2) - (seats - 1)
                hint = 'Count all pairs, then remove neighbouring pairs.'
                steps = [f'All pairs: C({seats}, 2) = {math.comb(seats, 2)}.', f'Neighbouring pairs: {seats - 1}.', f'The difference is {answer}.']
                diagram = _grid(1, seats, en)
            else:
                vals = [rng.randint(15, 60) * 10 for _ in range(3)]
                diff = max(vals) - min(vals)
                en = 'Using the table, how many more visitors came in the busiest month than in the quietest?'
                fr = 'En utilisant le tableau, combien de visiteurs de plus sont venus le mois le plus achalandé que le mois le plus calme ?'
                answer = diff
                hint = 'Find the largest and smallest numbers in the table.'
                steps = [f'Busiest: {max(vals):,} visitors.', f'Quietest: {min(vals):,} visitors.', f'Difference: {max(vals):,} − {min(vals):,} = {answer:,}.']
                diagram = _data_table(['Month', 'Visitors'], [['June', f'{vals[0]:,}'], ['July', f'{vals[1]:,}'], ['August', f'{vals[2]:,}']], en)
    elif grade <= 10:
        if slot == 0:
            variant = rng.randint(0, 2)
            if variant == 0:
                seats = grade - 2
                en = f'The row shows {seats} seats. In how many ways can you choose three seats so that no two chosen seats share a side?'
                fr = f'La rangée montre {seats} places. De combien de façons peut-on en choisir trois sans que deux places choisies soient voisines ?'
                answer = math.comb(seats - 2, 3)
                hint = 'Reserve one empty seat in each required gap between chosen seats.'
                steps = [f'After reserving the two gaps, choose 3 positions among {seats - 2}.', f'C({seats - 2}, 3) = {answer}.']
                diagram = _grid(1, seats, en)
            elif variant == 1:
                radicand, div = rng.choice([(11, 3), (7, 2), (19, 2), (29, 3), (5, 2), (23, 4), (13, 3), (17, 2), (31, 5)])
                v = math.sqrt(radicand) / div
                lo = int(v)
                en = f'The arrow marks the value of √{radicand} ÷ {div} on the number line. Between which two consecutive whole numbers does it lie?'
                fr = f'La flèche marque la valeur de √{radicand} ÷ {div} sur la droite numérique. Entre quels deux nombres entiers consécutifs se situe-t-elle ?'
                answer = f'{lo} and {lo + 1}'
                pool = [f'{i} and {i + 1}' for i in range(4)]
                choices = _text_choices(answer, pool, rng)
                hint = 'Estimate the square root first, then divide.'
                steps = [f'√{radicand} ≈ {math.sqrt(radicand):.2f}.',
                         f'{math.sqrt(radicand):.2f} ÷ {div} ≈ {v:.2f}.',
                         f'So the value lies between {lo} and {lo + 1}.']
                hi_line = lo + 2
                diagram = _number_line(0, hi_line, hi_line, v, en, tick_labels=set(range(hi_line + 1)))
            else:
                total = rng.choice([6, 8, 10, 12])
                shaded = rng.randint(2, total - 2)
                g = math.gcd(shaded, total)
                en = 'The spinner is split into equal sectors. What is the probability it lands on a shaded sector? Give the simplest fraction.'
                fr = 'La roue est divisée en secteurs égaux. Quelle est la probabilité qu’elle s’arrête sur un secteur gris ? Donne la fraction la plus simple.'
                answer = f'{shaded // g}/{total // g}'
                hint = 'Count shaded sectors out of all sectors, then simplify.'
                steps = [f'There are {shaded} shaded sectors out of {total}.', f'{shaded}/{total} simplifies to {answer}.']
                diagram = _wheel(shaded, total, en)
        else:
            variant = rng.randint(0, 2)
            if variant == 0:
                size = grade - 7
                en = f'How many shortest routes go from bottom-left to top-right on this {size} by {size} grid using only right and up moves?'
                fr = f'Combien de trajets les plus courts vont du coin inférieur gauche au coin supérieur droit sur cette grille de {size} sur {size}, seulement vers la droite ou vers le haut ?'
                answer = math.comb(2 * size, size)
                hint = 'Choose the positions of the up moves within the full route.'
                steps = [f'Every route has {2 * size} moves and {size} of them are up.', f'C({2 * size}, {size}) = {answer}.']
                diagram = _grid(size, size, en)
            elif variant == 1:
                shaded = rng.randint(2, 5)
                g = math.gcd(shaded, 6)
                en = 'The regular hexagon is split into 6 equal triangles. What fraction of it is shaded? Give the simplest fraction.'
                fr = 'L’hexagone régulier est divisé en 6 triangles égaux. Quelle fraction est grisée ? Donne la fraction la plus simple.'
                answer = f'{shaded // g}/{6 // g}'
                hint = 'All six triangles have the same area.'
                steps = [f'There are {shaded} shaded triangles out of 6.', f'{shaded}/6 simplifies to {answer}.']
                diagram = _hexagon(shaded, en)
            else:
                vals = sorted(rng.randint(1, 9) for _ in range(5))
                mean_num = rng.randint(4, 7)
                vals[-1] = mean_num * 5 - sum(vals[:4])
                while vals[-1] <= 0 or vals[-1] > 12:
                    vals = sorted(rng.randint(1, 9) for _ in range(5))
                    vals[-1] = mean_num * 5 - sum(vals[:4])
                vals = sorted(vals)
                en = 'Using the table, what is the mean number of goals scored per game?'
                fr = 'En utilisant le tableau, quelle est la moyenne de buts marqués par match ?'
                answer = mean_num
                hint = 'Add all five values, then divide by 5.'
                steps = [f'Total: {" + ".join(str(v) for v in vals)} = {sum(vals)}.', f'Mean: {sum(vals)} ÷ 5 = {answer}.']
                diagram = _data_table(['Game', 'Goals'], [[f'Game {i + 1}', v] for i, v in enumerate(vals)], en)
    else:
        if slot == 0:
            variant = rng.randint(0, 1)
            if variant == 0:
                size = grade - 8
                en = f'On this {size} by {size} grid, how many right/up routes from bottom-left to top-right never rise above the dashed diagonal?'
                fr = f'Sur cette grille de {size} sur {size}, combien de trajets vers la droite ou le haut vont du coin inférieur gauche au coin supérieur droit sans passer au-dessus de la diagonale pointillée ?'
                answer = math.comb(2 * size, size) // (size + 1)
                hint = 'Count unrestricted routes, then subtract routes that first cross the diagonal.'
                steps = [f'There are C({2 * size}, {size}) unrestricted routes.', f'Reflection gives C({2 * size}, {size - 1}) routes that cross.', f'The difference is {answer}.']
                diagram = _grid(size, size, en).replace('</svg>', f'<line x1="10" y1="{10 + size * 32}" x2="{10 + size * 32}" y2="10" stroke="#334155" stroke-dasharray="5 4"/></svg>')
            else:
                specs = []
                seen = set()
                while len(specs) < 4:
                    tot = rng.choice([4, 5, 6, 8])
                    sh = rng.randint(1, tot - 1)
                    if sh / tot in seen or (sh, tot) in specs:
                        continue
                    seen.add(sh / tot)
                    specs.append((sh, tot))
                probs = [s / t for s, t in specs]
                best = probs.index(max(probs))
                en = 'Each wheel is split into equal sectors; grey sectors win. Which wheel gives the best chance of winning?'
                fr = 'Chaque roue est divisée en secteurs égaux ; les secteurs gris gagnent. Quelle roue donne la meilleure chance de gagner ?'
                answer = f'Wheel {chr(65 + best)}'
                pool = [f'Wheel {chr(65 + i)}' for i in range(4)]
                choices = _text_choices(answer, pool, rng)
                hint = 'Compare each grey fraction using a common denominator or decimals.'
                steps = [f'Wheel {chr(65 + i)}: {s}/{t} = {s / t:.3f}' for i, (s, t) in enumerate(specs)] + [f'The largest probability is {probs[best]:.3f}, so {answer}.']
                diagram = _wheels(specs, en)
        else:
            variant = rng.randint(0, 1)
            if variant == 0:
                size = grade - 8
                en = f'On this {size} by {size} grid, how many right/up routes from bottom-left to top-right pass through the centre lattice point?'
                fr = f'Sur cette grille de {size} sur {size}, combien de trajets vers la droite ou le haut passent par le point central en allant du coin inférieur gauche au coin supérieur droit ?'
                answer = math.comb(size, size // 2) ** 2
                hint = 'Multiply the number of ways to reach the centre by the ways to leave it.'
                steps = [f'To reach the centre, arrange {size // 2} up moves among {size}: {math.comb(size, size // 2)} ways.', f'The second half also has {math.comb(size, size // 2)} ways.', f'Multiply to get {answer}.']
                center = 10 + size * 16
                diagram = _grid(size, size, en).replace('</svg>', f'<circle cx="{center}" cy="{center}" r="6" fill="#334155"/></svg>')
            else:
                made = rng.choice([56, 63, 70, 77])
                d1 = rng.choice([24, 30, 36])
                d2 = d1 // 2
                answer = made // 7
                en = f'A ball of yarn {d1} cm wide made exactly {made} identical socks. The ball that remains is {d2} cm wide. How many more socks can it make?'
                fr = f'Une pelote de laine de {d1} cm de large a permis de tricoter exactement {made} chaussettes identiques. La pelote restante fait {d2} cm. Combien de chaussettes peut-elle encore produire ?'
                hint = 'Yarn amount scales with volume, and volume scales with the cube of the diameter.'
                steps = [f'The diameter halved, so the remaining volume is (1/2)³ = 1/8 of the original.',
                         f'The {made} socks used 7/8 of the yarn.',
                         f'Each 1/8 makes {made} ÷ 7 = {answer} socks.']
                diagram = _yarn_balls(d1, d2, en)

    answer = str(answer)
    return dict(question=en, fr=fr, answer=answer, choices=choices if choices is not None else _choice_values(answer, rng), hint=hint, steps=steps,
                diagram=diagram, difficulty='hard')


def challenge_markdown(grade, day, slot=0):
    q = make_challenge(grade, day, slot)
    choices = '   '.join(f'{label}) {value}' for label, value in zip('ABCD', q['choices']))
    return (f"0. **[Hard] Math Challenge / Défi mathématique**\n"
            f"   - EN: {q['question']}\n   - FR: {q['fr']}\n   - Choices: {choices}\n"
            f"   - Diagram: CHALLENGE-DIAGRAM-G{grade}-Q{slot + 1}\n"
            f"   - Hint: {q['hint']}\n   - Steps:\n"
            + ''.join(f'     - {step}\n' for step in q['steps'])
            + f"   - Answer: {q['answer']}\n")


def inject_daily_challenges(text, day, replace_item=None):
    for grade in range(1, 13):
        pattern = rf'(## G{grade}\n)(.*?)(?=\n## |\Z)'
        def append(match):
            section = match.group(2).rstrip()
            if section.count('Math Challenge / Défi mathématique') >= 2:
                return match.group(0)
            numbers = [int(n) for n in re.findall(r'^(\d+)\.\s*\*\*\[', section, re.MULTILINE)]
            next_number = max(numbers, default=0) + 1
            additions = ''.join(
                re.sub(r'^\d+\.', f'{next_number + slot}.', challenge_markdown(grade, day, slot), count=1)
                for slot in range(2)
            )
            return match.group(1) + section + '\n\n' + additions
        text = re.sub(pattern, append, text, count=1, flags=re.DOTALL)
    return text


def render_challenge_diagrams(content, grade, day):
    for slot in range(2):
        content = content.replace(f'CHALLENGE-DIAGRAM-G{grade}-Q{slot + 1}', make_challenge(grade, day, slot)['diagram'])
    return content
