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


def _choice_values(answer, rng):
    answer = str(answer)
    if answer.isdigit():
        value = int(answer)
        values = {value, value + 1, value + 2, max(0, value - 1)}
        while len(values) < 4:
            values.add(value + len(values) + 2)
        choices = [str(v) for v in values]
    else:
        choices = [answer]
        pool = ['Yes / oui', 'No / non', 'Left / gauche', 'Right / droite', 'A', 'B', 'C']
        for item in pool:
            if item != answer and len(choices) < 4:
                choices.append(item)
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
            cols = grade
            en = f'How many rectangles of any size can be traced along the lines of this 2 by {cols} grid? Count squares as rectangles too.'
            fr = f'Combien de rectangles de toutes tailles peut-on tracer sur les lignes de cette grille de 2 sur {cols} ? Compte aussi les carrés.'
            answer = 3 * math.comb(cols + 1, 2)
            hint = 'Choose a left/right pair of vertical lines, then choose a top/bottom pair.'
            steps = [f'There are {math.comb(cols + 1, 2)} pairs of vertical grid lines.', 'There are 3 pairs of horizontal grid lines.', f'Multiply to get {answer}.']
            diagram = _grid(2, cols, en)
        else:
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
    elif grade <= 6:
        if slot == 0:
            en = f'On this 2 by {n} grid, how many shortest routes go from the bottom-left corner to the top-right corner using only right and up moves?'
            fr = f'Sur cette grille de 2 sur {n}, combien de trajets les plus courts vont du coin inférieur gauche au coin supérieur droit, seulement vers la droite ou vers le haut ?'
            answer = math.comb(n + 2, 2)
            hint = 'Choose which two moves in the route go up.'
            steps = [f'Each shortest route has {n} right moves and 2 up moves.', f'Choose the two up positions to get C({n + 2}, 2) = {answer}.']
            diagram = _grid(2, n, en)
        else:
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
    elif grade <= 8:
        if slot == 0:
            moves = 2 * n + 1
            en = f'A counter starts on a grey square. Each move goes to a square sharing a side. After {moves} moves, what type of square must it occupy?'
            fr = f'Un pion part d’une case grise. Chaque déplacement mène à une case voisine par un côté. Après {moves} déplacements, sur quel type de case est-il forcément ?'
            answer = 'White / blanche'
            hint = 'Track the colour after one move, then after two moves.'
            steps = ['Every move changes the colour.', f'{moves} is odd, so the final colour is the opposite of the starting colour.']
            diagram = _grid(4, 4, en, shaded=True)
        else:
            seats = n + 4
            en = f'The row shows {seats} seats. In how many ways can you choose two seats that do not share a side?'
            fr = f'La rangée montre {seats} places. De combien de façons peut-on choisir deux places qui ne se touchent pas par un côté ?'
            answer = math.comb(seats, 2) - (seats - 1)
            hint = 'Count all pairs, then remove neighbouring pairs.'
            steps = [f'All pairs: C({seats}, 2) = {math.comb(seats, 2)}.', f'Neighbouring pairs: {seats - 1}.', f'The difference is {answer}.']
            diagram = _grid(1, seats, en)
    elif grade <= 10:
        if slot == 0:
            seats = grade - 2
            en = f'The row shows {seats} seats. In how many ways can you choose three seats so that no two chosen seats share a side?'
            fr = f'La rangée montre {seats} places. De combien de façons peut-on en choisir trois sans que deux places choisies soient voisines ?'
            answer = math.comb(seats - 2, 3)
            hint = 'Reserve one empty seat in each required gap between chosen seats.'
            steps = [f'After reserving the two gaps, choose 3 positions among {seats - 2}.', f'C({seats - 2}, 3) = {answer}.']
            diagram = _grid(1, seats, en)
        else:
            size = grade - 7
            en = f'How many shortest routes go from bottom-left to top-right on this {size} by {size} grid using only right and up moves?'
            fr = f'Combien de trajets les plus courts vont du coin inférieur gauche au coin supérieur droit sur cette grille de {size} sur {size}, seulement vers la droite ou vers le haut ?'
            answer = math.comb(2 * size, size)
            hint = 'Choose the positions of the up moves within the full route.'
            steps = [f'Every route has {2 * size} moves and {size} of them are up.', f'C({2 * size}, {size}) = {answer}.']
            diagram = _grid(size, size, en)
    else:
        if slot == 0:
            size = grade - 8
            en = f'On this {size} by {size} grid, how many right/up routes from bottom-left to top-right never rise above the dashed diagonal?'
            fr = f'Sur cette grille de {size} sur {size}, combien de trajets vers la droite ou le haut vont du coin inférieur gauche au coin supérieur droit sans passer au-dessus de la diagonale pointillée ?'
            answer = math.comb(2 * size, size) // (size + 1)
            hint = 'Count unrestricted routes, then subtract routes that first cross the diagonal.'
            steps = [f'There are C({2 * size}, {size}) unrestricted routes.', f'Reflection gives C({2 * size}, {size - 1}) routes that cross.', f'The difference is {answer}.']
            diagram = _grid(size, size, en).replace('</svg>', f'<line x1="10" y1="{10 + size * 32}" x2="{10 + size * 32}" y2="10" stroke="#334155" stroke-dasharray="5 4"/></svg>')
        else:
            size = grade - 8
            en = f'On this {size} by {size} grid, how many right/up routes from bottom-left to top-right pass through the centre lattice point?'
            fr = f'Sur cette grille de {size} sur {size}, combien de trajets vers la droite ou le haut passent par le point central en allant du coin inférieur gauche au coin supérieur droit ?'
            answer = math.comb(size, size // 2) ** 2
            hint = 'Multiply the number of ways to reach the centre by the ways to leave it.'
            steps = [f'To reach the centre, arrange {size // 2} up moves among {size}: {math.comb(size, size // 2)} ways.', f'The second half also has {math.comb(size, size // 2)} ways.', f'Multiply to get {answer}.']
            center = 10 + size * 16
            diagram = _grid(size, size, en).replace('</svg>', f'<circle cx="{center}" cy="{center}" r="6" fill="#334155"/></svg>')

    answer = str(answer)
    return dict(question=en, fr=fr, answer=answer, choices=_choice_values(answer, rng), hint=hint, steps=steps,
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
