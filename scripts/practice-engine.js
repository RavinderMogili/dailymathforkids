// ── Practice Mode Question Generator ─────────────────────────────────────
// Generates math questions algorithmically based on grade, topic, difficulty.

const TOPICS_BY_GRADE = {
  1: ['Addition & Subtraction', 'Place Value', 'Counting', 'Measurement', 'Geometry'],
  2: ['Addition & Subtraction', 'Place Value', 'Measurement', 'Money', 'Geometry'],
  3: ['Multiplication & Division', 'Fractions', 'Place Value', 'Measurement', 'Geometry'],
  4: ['Multi-digit Arithmetic', 'Fractions', 'Decimals', 'Measurement', 'Geometry'],
  5: ['Decimals', 'Fractions', 'Order of Operations', 'Volume', 'Coordinate Plane'],
  6: ['Ratios & Proportions', 'Integers', 'Expressions & Equations', 'Area & Surface Area', 'Statistics'],
  7: ['Proportional Relationships', 'Operations with Rationals', 'Expressions & Equations', 'Geometry', 'Probability & Statistics'],
  8: ['Linear Equations', 'Functions', 'Exponents & Roots', 'Pythagorean Theorem', 'Transformations'],
  9: ['Linear Functions', 'Quadratic Equations', 'Polynomials', 'Inequalities', 'Data Analysis'],
  10: ['Quadratics', 'Trigonometry', 'Circle Geometry', 'Coordinate Geometry', 'Systems of Equations'],
  11: ['Functions', 'Exponential & Logarithmic', 'Sequences & Series', 'Trigonometric Functions', 'Financial Math'],
  12: ['Limits & Derivatives', 'Advanced Functions', 'Probability & Statistics', 'Vectors', 'Proof & Logic'],
};

function getTopicsForGrade(grade) {
  return TOPICS_BY_GRADE[grade] || TOPICS_BY_GRADE[3];
}

// ── Helpers ──────────────────────────────────────────────────────────────
function randInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function shuffle(arr) { for (let i = arr.length - 1; i > 0; i--) { const j = randInt(0, i); [arr[i], arr[j]] = [arr[j], arr[i]]; } return arr; }
function pick(arr) { return arr[randInt(0, arr.length - 1)]; }
function round2(n) { return Math.round(n * 100) / 100; }
function gcd(a, b) { return b === 0 ? a : gcd(b, a % b); }

function makeChoices(correct, count = 4, gen) {
  const choices = new Set([String(correct)]);
  let tries = 0;
  while (choices.size < count && tries < 50) {
    const wrong = gen();
    if (String(wrong) !== String(correct)) choices.add(String(wrong));
    tries++;
  }
  while (choices.size < count) choices.add(String(correct + choices.size));
  return shuffle([...choices]);
}

// ── Grade 1-2: Addition & Subtraction ────────────────────────────────────
function genAddSub(grade, difficulty) {
  const ranges = {
    easy:   grade <= 2 ? [1, 10] : [1, 20],
    medium: grade <= 2 ? [1, 20] : [10, 50],
    hard:   grade <= 2 ? [5, 50] : [20, 100],
  };
  const [lo, hi] = ranges[difficulty];
  const isAdd = Math.random() > 0.4;
  if (isAdd) {
    const a = randInt(lo, hi), b = randInt(lo, hi);
    const ans = a + b;
    return { question: `${a} + ${b} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-5, 5)) };
  } else {
    const b = randInt(lo, Math.floor(hi / 2)), a = b + randInt(lo, hi);
    const ans = a - b;
    return { question: `${a} − ${b} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-5, 5)) };
  }
}

// ── Grade 1-2: Place Value ───────────────────────────────────────────────
function genPlaceValue(grade, difficulty) {
  if (difficulty === 'easy') {
    const n = randInt(10, 99);
    const tens = Math.floor(n / 10), ones = n % 10;
    const askTens = Math.random() > 0.5;
    const ans = askTens ? tens : ones;
    return { question: `What is the ${askTens ? 'tens' : 'ones'} digit of ${n}?`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(0, 9)) };
  } else if (difficulty === 'medium') {
    const n = grade >= 2 ? randInt(100, 999) : randInt(10, 99);
    const digits = grade >= 2 ? ['hundreds', 'tens', 'ones'] : ['tens', 'ones'];
    const which = pick(digits);
    const ans = which === 'hundreds' ? Math.floor(n / 100) : which === 'tens' ? Math.floor((n % 100) / 10) : n % 10;
    return { question: `What is the ${which} digit of ${n}?`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(0, 9)) };
  } else {
    const a = randInt(100, 999), b = randInt(100, 999);
    const ans = a > b ? '>' : a < b ? '<' : '=';
    return { question: `Compare: ${a} ___ ${b}`, answer: ans, choices: ['>', '<', '=', `${a > b ? '<' : '>'}`] };
  }
}

// ── Grade 1-2: Counting ─────────────────────────────────────────────────
function genCounting(grade, difficulty) {
  const skipBy = difficulty === 'easy' ? pick([2, 5, 10]) : difficulty === 'medium' ? pick([3, 4, 5]) : pick([6, 7, 8, 9]);
  const start = randInt(0, 20) * skipBy;
  const steps = randInt(3, 5);
  const seq = [];
  for (let i = 0; i < steps; i++) seq.push(start + i * skipBy);
  const ans = start + steps * skipBy;
  return { question: `What comes next? ${seq.join(', ')}, ?`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-2, 2) * skipBy) };
}

// ── Grade 1-2: Measurement ──────────────────────────────────────────────
function genMeasurement12(grade, difficulty) {
  if (difficulty === 'easy') {
    const hr = randInt(1, 12);
    return { question: `A clock shows ${hr}:00. What hour is it?`, answer: String(hr), choices: makeChoices(hr, 4, () => randInt(1, 12)) };
  } else {
    const items = ['pencil', 'book', 'desk', 'eraser', 'ruler'];
    const a = pick(items), aLen = randInt(3, 30);
    let b; do { b = pick(items); } while (b === a);
    const bLen = randInt(3, 30);
    const ans = aLen > bLen ? a : b;
    return { question: `A ${a} is ${aLen} cm. A ${b} is ${bLen} cm. Which is longer?`, answer: ans, choices: [a, b, 'Same', 'Not sure'] };
  }
}

// ── Grade 1-2: Geometry ─────────────────────────────────────────────────
function genGeometry12(grade, difficulty) {
  const shapes = [
    { name: 'triangle', sides: 3 },
    { name: 'square', sides: 4 },
    { name: 'rectangle', sides: 4 },
    { name: 'pentagon', sides: 5 },
    { name: 'hexagon', sides: 6 },
    { name: 'circle', sides: 0 },
  ];
  const s = pick(shapes.filter(x => x.sides > 0));
  if (difficulty === 'easy') {
    return { question: `How many sides does a ${s.name} have?`, answer: String(s.sides), choices: makeChoices(s.sides, 4, () => randInt(2, 8)) };
  } else {
    return { question: `Which shape has ${s.sides} sides?`, answer: s.name, choices: shuffle(shapes.filter(x => x.sides > 0).slice(0, 4).map(x => x.name)) };
  }
}

// ── Grade 2: Money ──────────────────────────────────────────────────────
function genMoney(grade, difficulty) {
  const coins = difficulty === 'easy' ? [1, 5, 10] : [1, 5, 10, 25];
  const count = difficulty === 'easy' ? randInt(2, 3) : difficulty === 'medium' ? randInt(3, 5) : randInt(4, 6);
  let total = 0;
  const parts = [];
  for (let i = 0; i < count; i++) { const c = pick(coins); total += c; parts.push(c + '¢'); }
  return { question: `How much is ${parts.join(' + ')}?`, answer: total + '¢', choices: makeChoices(total + '¢', 4, () => (total + randInt(-10, 10)) + '¢') };
}

// ── Grade 3+: Multiplication & Division ─────────────────────────────────
function genMulDiv(grade, difficulty) {
  const maxFactor = difficulty === 'easy' ? 5 : difficulty === 'medium' ? 10 : 12;
  const isMul = Math.random() > 0.4;
  if (isMul) {
    const a = randInt(2, maxFactor), b = randInt(2, maxFactor);
    const ans = a * b;
    return { question: `${a} × ${b} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(2, maxFactor) * randInt(2, maxFactor)) };
  } else {
    const b = randInt(2, maxFactor), ans = randInt(2, maxFactor);
    const a = b * ans;
    return { question: `${a} ÷ ${b} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(1, maxFactor * 2)) };
  }
}

// ── Grade 3+: Fractions ─────────────────────────────────────────────────
function genFractions(grade, difficulty) {
  if (grade <= 4 && difficulty === 'easy') {
    const d = pick([2, 3, 4, 6, 8]);
    const n = randInt(1, d - 1);
    const g = gcd(n, d);
    const sn = n / g, sd = d / g;
    return { question: `Simplify ${n}/${d}`, answer: `${sn}/${sd}`, choices: makeChoices(`${sn}/${sd}`, 4, () => `${randInt(1, d)}/${randInt(2, d + 2)}`) };
  } else if (difficulty === 'medium') {
    const d = pick([2, 4, 5, 8, 10]);
    const n1 = randInt(1, d - 1), n2 = randInt(1, d - 1);
    const sum = n1 + n2;
    const g = gcd(sum, d);
    const ans = sum >= d ? `${Math.floor(sum / d)} ${(sum % d) / g}/${d / g}` : `${sum / g}/${d / g}`;
    return { question: `${n1}/${d} + ${n2}/${d} = ?`, answer: ans.replace(/ 0\/\d+/, ''), choices: makeChoices(ans, 4, () => `${randInt(1, d * 2)}/${d}`) };
  } else {
    const d1 = pick([2, 3, 4, 5, 6]), d2 = pick([2, 3, 4, 5, 6]);
    const n1 = randInt(1, d1), n2 = randInt(1, d2);
    const lcd = (d1 * d2) / gcd(d1, d2);
    const sum = n1 * (lcd / d1) + n2 * (lcd / d2);
    const g = gcd(sum, lcd);
    return { question: `${n1}/${d1} + ${n2}/${d2} = ?`, answer: `${sum / g}/${lcd / g}`, choices: makeChoices(`${sum / g}/${lcd / g}`, 4, () => `${randInt(1, 12)}/${randInt(2, 12)}`) };
  }
}

// ── Grade 4+: Multi-digit Arithmetic ────────────────────────────────────
function genMultiDigit(grade, difficulty) {
  if (difficulty === 'easy') {
    const a = randInt(10, 99), b = randInt(2, 9);
    const ans = a * b;
    return { question: `${a} × ${b} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => a * randInt(2, 9)) };
  } else if (difficulty === 'medium') {
    const a = randInt(100, 999), b = randInt(2, 9);
    const ans = a * b;
    return { question: `${a} × ${b} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-50, 50)) };
  } else {
    const b = randInt(2, 9), ans = randInt(10, 99);
    const a = b * ans + randInt(0, b - 1);
    const q = Math.floor(a / b);
    const r = a % b;
    const ansStr = r > 0 ? `${q} R${r}` : String(q);
    return { question: `${a} ÷ ${b} = ?`, answer: ansStr, choices: makeChoices(ansStr, 4, () => r > 0 ? `${q + randInt(-3, 3)} R${randInt(0, b)}` : String(q + randInt(-5, 5))) };
  }
}

// ── Grade 4+: Decimals ──────────────────────────────────────────────────
function genDecimals(grade, difficulty) {
  if (difficulty === 'easy') {
    const a = round2(randInt(1, 20) + randInt(1, 9) / 10);
    const b = round2(randInt(1, 20) + randInt(1, 9) / 10);
    const ans = round2(a + b);
    return { question: `${a} + ${b} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => round2(ans + randInt(-2, 2) + randInt(-5, 5) / 10)) };
  } else if (difficulty === 'medium') {
    const a = round2(randInt(1, 15) + randInt(1, 99) / 100);
    const b = round2(randInt(1, 9) + randInt(1, 99) / 100);
    const ans = round2(a * b);
    return { question: `${a} × ${b} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => round2(ans + randInt(-5, 5))) };
  } else {
    const b = round2(randInt(2, 9) + randInt(1, 9) / 10);
    const ans = round2(randInt(2, 20) + randInt(0, 9) / 10);
    const a = round2(b * ans);
    return { question: `${a} ÷ ${b} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => round2(ans + randInt(-3, 3))) };
  }
}

// ── Grade 5: Order of Operations ────────────────────────────────────────
function genOrderOfOps(grade, difficulty) {
  if (difficulty === 'easy') {
    const a = randInt(2, 10), b = randInt(2, 5), c = randInt(1, 10);
    const ans = a + b * c;
    return { question: `${a} + ${b} × ${c} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-10, 10)) };
  } else if (difficulty === 'medium') {
    const a = randInt(2, 8), b = randInt(2, 8), c = randInt(1, 5);
    const ans = (a + b) * c;
    return { question: `(${a} + ${b}) × ${c} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-10, 10)) };
  } else {
    const a = randInt(2, 6), b = randInt(1, 4), c = randInt(2, 5), d = randInt(1, 8);
    const ans = a * b + c * d;
    return { question: `${a} × ${b} + ${c} × ${d} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-8, 8)) };
  }
}

// ── Grade 6: Ratios & Proportions ───────────────────────────────────────
function genRatios(grade, difficulty) {
  if (difficulty === 'easy') {
    const a = randInt(1, 10), b = randInt(1, 10);
    const g = gcd(a, b);
    return { question: `Simplify the ratio ${a}:${b}`, answer: `${a / g}:${b / g}`, choices: makeChoices(`${a / g}:${b / g}`, 4, () => `${randInt(1, 10)}:${randInt(1, 10)}`) };
  } else {
    const a = randInt(2, 8), b = randInt(2, 8), mult = randInt(2, 5);
    const ans = b * mult;
    return { question: `If ${a}:${b} = ${a * mult}:?, find ?`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(2, 40)) };
  }
}

// ── Grade 6: Integers ───────────────────────────────────────────────────
function genIntegers(grade, difficulty) {
  const range = difficulty === 'easy' ? 10 : difficulty === 'medium' ? 20 : 50;
  const a = randInt(-range, range), b = randInt(-range, range);
  const ops = difficulty === 'hard' ? ['+', '-', '×'] : ['+', '-'];
  const op = pick(ops);
  const ans = op === '+' ? a + b : op === '-' ? a - b : a * b;
  const display = op === '×' ? '×' : op;
  return { question: `(${a}) ${display} (${b}) = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-8, 8)) };
}

// ── Grade 6: Expressions & Equations ────────────────────────────────────
function genExpressions(grade, difficulty) {
  if (difficulty === 'easy' || grade <= 6) {
    const a = randInt(2, 10), ans = randInt(1, 15);
    const b = a * ans;
    return { question: `Solve: ${a}x = ${b}`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(1, 20)) };
  } else {
    const a = randInt(2, 8), b = randInt(1, 15), ans = randInt(1, 12);
    const c = a * ans + b;
    return { question: `Solve: ${a}x + ${b} = ${c}`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(1, 15)) };
  }
}

// ── Grade 6: Statistics ─────────────────────────────────────────────────
function genStatistics(grade, difficulty) {
  const count = difficulty === 'easy' ? 4 : difficulty === 'medium' ? 5 : 6;
  const nums = [];
  for (let i = 0; i < count; i++) nums.push(randInt(1, 20));
  const sorted = [...nums].sort((a, b) => a - b);
  const sum = nums.reduce((s, n) => s + n, 0);
  const askType = pick(difficulty === 'easy' ? ['mean'] : ['mean', 'median']);
  if (askType === 'mean') {
    const ans = round2(sum / count);
    return { question: `Find the mean: ${nums.join(', ')}`, answer: String(ans), choices: makeChoices(ans, 4, () => round2(ans + randInt(-3, 3))) };
  } else {
    const mid = Math.floor(count / 2);
    const ans = count % 2 === 0 ? round2((sorted[mid - 1] + sorted[mid]) / 2) : sorted[mid];
    return { question: `Find the median: ${nums.join(', ')}`, answer: String(ans), choices: makeChoices(ans, 4, () => sorted[randInt(0, count - 1)]) };
  }
}

// ── Grade 5: Volume ─────────────────────────────────────────────────────
function genVolume(grade, difficulty) {
  const l = randInt(2, difficulty === 'easy' ? 5 : 10);
  const w = randInt(2, difficulty === 'easy' ? 5 : 10);
  const h = randInt(2, difficulty === 'easy' ? 5 : 8);
  const ans = l * w * h;
  return { question: `A box is ${l} × ${w} × ${h}. What is the volume?`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(2, 10) * randInt(2, 10) * randInt(2, 10)) };
}

// ── Grade 6: Area & Surface Area ────────────────────────────────────────
function genArea(grade, difficulty) {
  if (difficulty === 'easy') {
    const l = randInt(2, 12), w = randInt(2, 12);
    const ans = l * w;
    return { question: `Area of a rectangle: length = ${l}, width = ${w}`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(2, 12) * randInt(2, 12)) };
  } else {
    const b = randInt(3, 15), h = randInt(3, 15);
    const ans = round2(0.5 * b * h);
    return { question: `Area of a triangle: base = ${b}, height = ${h}`, answer: String(ans), choices: makeChoices(ans, 4, () => round2(0.5 * randInt(3, 15) * randInt(3, 15))) };
  }
}

// ── Grade 7+: Proportional Relationships ────────────────────────────────
function genProportional(grade, difficulty) {
  const rate = randInt(2, 12);
  const x = randInt(3, difficulty === 'easy' ? 8 : 15);
  const ans = rate * x;
  return { question: `If 1 item costs $${rate}, how much do ${x} items cost?`, answer: '$' + ans, choices: makeChoices('$' + ans, 4, () => '$' + (rate * randInt(2, 15))) };
}

// ── Grade 7: Probability ────────────────────────────────────────────────
function genProbability(grade, difficulty) {
  const total = pick([6, 8, 10, 12]);
  const favorable = randInt(1, total - 1);
  const g = gcd(favorable, total);
  return { question: `A bag has ${total} balls. ${favorable} are red. What is the probability of picking red?`, answer: `${favorable / g}/${total / g}`, choices: makeChoices(`${favorable / g}/${total / g}`, 4, () => `${randInt(1, total)}/${total}`) };
}

// ── Grade 8: Linear Equations ───────────────────────────────────────────
function genLinearEq(grade, difficulty) {
  const m = randInt(-5, 5) || 1;
  const b = randInt(-10, 10);
  if (difficulty === 'easy') {
    const x = randInt(-5, 5);
    const y = m * x + b;
    return { question: `If y = ${m}x + ${b}, what is y when x = ${x}?`, answer: String(y), choices: makeChoices(y, 4, () => y + randInt(-6, 6)) };
  } else {
    return { question: `What is the slope of y = ${m}x + ${b}?`, answer: String(m), choices: makeChoices(m, 4, () => randInt(-5, 5)) };
  }
}

// ── Grade 8: Exponents & Roots ──────────────────────────────────────────
function genExponents(grade, difficulty) {
  if (difficulty === 'easy') {
    const base = randInt(2, 6), exp = randInt(2, 3);
    const ans = Math.pow(base, exp);
    return { question: `${base}^${exp} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => Math.pow(randInt(2, 6), randInt(2, 3))) };
  } else if (difficulty === 'medium') {
    const perfect = pick([4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144]);
    const ans = Math.sqrt(perfect);
    return { question: `√${perfect} = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(2, 12)) };
  } else {
    const a = randInt(2, 5), b = randInt(1, 3);
    const ans = a + b;
    const base = randInt(2, 4);
    return { question: `Simplify: ${base}^${a} × ${base}^${b} = ${base}^?`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(2, 10)) };
  }
}

// ── Grade 8: Pythagorean Theorem ────────────────────────────────────────
function genPythagoras(grade, difficulty) {
  const triples = [[3, 4, 5], [5, 12, 13], [6, 8, 10], [8, 15, 17], [7, 24, 25]];
  const [a, b, c] = pick(difficulty === 'easy' ? triples.slice(0, 3) : triples);
  const askC = Math.random() > 0.3;
  if (askC) {
    return { question: `Right triangle: a = ${a}, b = ${b}. Find c.`, answer: String(c), choices: makeChoices(c, 4, () => randInt(c - 4, c + 4)) };
  } else {
    return { question: `Right triangle: a = ${a}, c = ${c}. Find b.`, answer: String(b), choices: makeChoices(b, 4, () => randInt(b - 4, b + 4)) };
  }
}

// ── Grade 9: Quadratic Equations ────────────────────────────────────────
function genQuadratics(grade, difficulty) {
  const r1 = randInt(-6, 6), r2 = randInt(-6, 6);
  const b = -(r1 + r2), c = r1 * r2;
  const bStr = b >= 0 ? `+ ${b}` : `− ${Math.abs(b)}`;
  const cStr = c >= 0 ? `+ ${c}` : `− ${Math.abs(c)}`;
  if (difficulty === 'easy') {
    return { question: `Factor: x² ${bStr}x ${cStr} = 0. Find one root.`, answer: String(r1), choices: makeChoices(r1, 4, () => randInt(-8, 8)) };
  } else {
    const sum = r1 + r2;
    return { question: `x² ${bStr}x ${cStr} = 0. Sum of roots?`, answer: String(sum), choices: makeChoices(sum, 4, () => randInt(-12, 12)) };
  }
}

// ── Grade 9: Polynomials ────────────────────────────────────────────────
function genPolynomials(grade, difficulty) {
  const a1 = randInt(1, 5), a2 = randInt(1, 5);
  const b1 = randInt(-8, 8), b2 = randInt(-8, 8);
  const sumA = a1 + a2, sumB = b1 + b2;
  const bStr = sumB >= 0 ? `+ ${sumB}` : `− ${Math.abs(sumB)}`;
  return { question: `(${a1}x ${b1 >= 0 ? '+ ' + b1 : '− ' + Math.abs(b1)}) + (${a2}x ${b2 >= 0 ? '+ ' + b2 : '− ' + Math.abs(b2)}) = ?`, answer: `${sumA}x ${bStr}`, choices: makeChoices(`${sumA}x ${bStr}`, 4, () => `${randInt(1, 10)}x ${randInt(-10, 10) >= 0 ? '+ ' + randInt(0, 10) : '− ' + randInt(1, 10)}`) };
}

// ── Grade 9: Inequalities ───────────────────────────────────────────────
function genInequalities(grade, difficulty) {
  const a = randInt(2, 8), b = randInt(1, 20);
  const ans = Math.floor(b / a);
  return { question: `Solve: ${a}x ≤ ${b}. Largest integer x?`, answer: String(ans), choices: makeChoices(ans, 4, () => randInt(0, ans + 4)) };
}

// ── Grade 10: Trigonometry ──────────────────────────────────────────────
function genTrig(grade, difficulty) {
  const triples = [[3, 4, 5], [5, 12, 13], [8, 15, 17]];
  const [opp, adj, hyp] = pick(triples);
  const func = pick(['sin', 'cos', 'tan']);
  const ans = func === 'sin' ? `${opp}/${hyp}` : func === 'cos' ? `${adj}/${hyp}` : `${opp}/${adj}`;
  return { question: `Right triangle: opposite = ${opp}, adjacent = ${adj}, hypotenuse = ${hyp}. ${func}(θ) = ?`, answer: ans, choices: makeChoices(ans, 4, () => `${pick([opp, adj, hyp])}/${pick([opp, adj, hyp])}`) };
}

// ── Grade 10+: Systems of Equations ─────────────────────────────────────
function genSystems(grade, difficulty) {
  const x = randInt(-5, 5), y = randInt(-5, 5);
  const a1 = randInt(1, 4), b1 = randInt(1, 4);
  const c1 = a1 * x + b1 * y;
  return { question: `If ${a1}x + ${b1}y = ${c1} and x = ${x}, find y.`, answer: String(y), choices: makeChoices(y, 4, () => randInt(-8, 8)) };
}

// ── Grade 11: Sequences & Series ────────────────────────────────────────
function genSequences(grade, difficulty) {
  if (difficulty !== 'hard') {
    const a1 = randInt(1, 10), d = randInt(1, 8);
    const n = randInt(5, 10);
    const ans = a1 + (n - 1) * d;
    return { question: `Arithmetic sequence: first = ${a1}, common difference = ${d}. Find term ${n}.`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-10, 10)) };
  } else {
    const a1 = randInt(1, 5), r = randInt(2, 3);
    const n = randInt(3, 5);
    const ans = a1 * Math.pow(r, n - 1);
    return { question: `Geometric sequence: first = ${a1}, ratio = ${r}. Find term ${n}.`, answer: String(ans), choices: makeChoices(ans, 4, () => a1 * Math.pow(r, randInt(1, 5))) };
  }
}

// ── Grade 11: Financial Math ────────────────────────────────────────────
function genFinancial(grade, difficulty) {
  const P = pick([100, 200, 500, 1000]);
  const r = pick([5, 8, 10]);
  const t = randInt(1, difficulty === 'easy' ? 3 : 5);
  const interest = P * r * t / 100;
  return { question: `Simple interest: $${P} at ${r}% for ${t} years. Interest earned?`, answer: '$' + interest, choices: makeChoices('$' + interest, 4, () => '$' + (P * pick([5, 8, 10]) * randInt(1, 5) / 100)) };
}

// ── Grade 12: Limits ────────────────────────────────────────────────────
function genLimits(grade, difficulty) {
  const a = randInt(1, 5), b = randInt(1, 8);
  const x = randInt(1, 5);
  const ans = a * x + b;
  return { question: `lim(x→${x}) of (${a}x + ${b}) = ?`, answer: String(ans), choices: makeChoices(ans, 4, () => ans + randInt(-5, 5)) };
}

// ── Grade 12: Vectors ───────────────────────────────────────────────────
function genVectors(grade, difficulty) {
  const a = [randInt(-5, 5), randInt(-5, 5)];
  const b = [randInt(-5, 5), randInt(-5, 5)];
  if (difficulty !== 'hard') {
    const ans = `(${a[0] + b[0]}, ${a[1] + b[1]})`;
    return { question: `Add vectors (${a[0]}, ${a[1]}) + (${b[0]}, ${b[1]}) = ?`, answer: ans, choices: makeChoices(ans, 4, () => `(${randInt(-10, 10)}, ${randInt(-10, 10)})`) };
  } else {
    const dot = a[0] * b[0] + a[1] * b[1];
    return { question: `Dot product: (${a[0]}, ${a[1]}) · (${b[0]}, ${b[1]}) = ?`, answer: String(dot), choices: makeChoices(dot, 4, () => dot + randInt(-8, 8)) };
  }
}

// ── Master dispatcher ───────────────────────────────────────────────────
const GENERATORS = {
  'Addition & Subtraction': genAddSub,
  'Place Value': genPlaceValue,
  'Counting': genCounting,
  'Measurement': genMeasurement12,
  'Geometry': (g, d) => g <= 3 ? genGeometry12(g, d) : genArea(g, d),
  'Money': genMoney,
  'Multiplication & Division': genMulDiv,
  'Fractions': genFractions,
  'Multi-digit Arithmetic': genMultiDigit,
  'Decimals': genDecimals,
  'Order of Operations': genOrderOfOps,
  'Volume': genVolume,
  'Coordinate Plane': (g, d) => genLinearEq(g, d),
  'Ratios & Proportions': genRatios,
  'Integers': genIntegers,
  'Expressions & Equations': genExpressions,
  'Area & Surface Area': genArea,
  'Statistics': genStatistics,
  'Proportional Relationships': genProportional,
  'Operations with Rationals': (g, d) => genDecimals(g, d),
  'Probability & Statistics': genProbability,
  'Linear Equations': genLinearEq,
  'Functions': (g, d) => genLinearEq(g, d),
  'Exponents & Roots': genExponents,
  'Pythagorean Theorem': genPythagoras,
  'Transformations': (g, d) => genGeometry12(g, d),
  'Linear Functions': genLinearEq,
  'Quadratic Equations': genQuadratics,
  'Quadratics': genQuadratics,
  'Polynomials': genPolynomials,
  'Inequalities': genInequalities,
  'Data Analysis': genStatistics,
  'Trigonometry': genTrig,
  'Trigonometric Functions': genTrig,
  'Circle Geometry': genArea,
  'Coordinate Geometry': genLinearEq,
  'Systems of Equations': genSystems,
  'Exponential & Logarithmic': genExponents,
  'Sequences & Series': genSequences,
  'Financial Math': genFinancial,
  'Limits & Derivatives': genLimits,
  'Advanced Functions': genPolynomials,
  'Vectors': genVectors,
  'Proof & Logic': genExponents,
};

// ── Hint generator ──────────────────────────────────────────────────────
const HINTS = {
  'Addition & Subtraction': q => q.question.includes('+') ? 'Add the numbers together. Try breaking them into tens and ones.' : 'Subtract the smaller number from the larger one.',
  'Place Value': () => 'Look at each digit\'s position: ones, tens, hundreds from right to left.',
  'Counting': () => 'Find the pattern: what number is being added each time?',
  'Measurement': () => 'Compare the numbers. The larger number means longer or bigger.',
  'Geometry': q => q.question.includes('sides') ? 'Count the straight edges of the shape.' : 'Think about the properties of each shape.',
  'Money': () => 'Add up all the coin values. 1¢, 5¢ (nickel), 10¢ (dime), 25¢ (quarter).',
  'Multiplication & Division': q => q.question.includes('×') ? 'Multiply: think of it as groups. e.g., 3 × 4 = 3 groups of 4.' : 'Division is the reverse of multiplication. What times the divisor gives you the number?',
  'Fractions': q => q.question.includes('Simplify') ? 'Divide both top and bottom by the same number.' : 'Find a common denominator first, then add the tops.',
  'Multi-digit Arithmetic': q => q.question.includes('×') ? 'Break the big number into parts, multiply each, then add.' : 'How many times does the divisor fit into the number?',
  'Decimals': () => 'Line up the decimal points, then compute like whole numbers.',
  'Order of Operations': () => 'Remember BEDMAS/PEMDAS: Brackets first, then Exponents, Division/Multiplication, Addition/Subtraction.',
  'Ratios & Proportions': () => 'Divide both sides by the same number to simplify.',
  'Integers': () => 'Two negatives make a positive when multiplying. Adding a negative is like subtracting.',
  'Expressions & Equations': () => 'Get x alone on one side. Do the same operation to both sides.',
  'Statistics': q => q.question.includes('mean') ? 'Mean = add all numbers, then divide by how many there are.' : 'Median = put numbers in order, pick the middle one.',
  'Volume': () => 'Volume = length × width × height.',
  'Area & Surface Area': q => q.question.includes('triangle') ? 'Area of triangle = ½ × base × height.' : 'Area of rectangle = length × width.',
  'Proportional Relationships': () => 'Multiply the rate by the quantity.',
  'Probability & Statistics': () => 'Probability = favorable outcomes ÷ total outcomes.',
  'Linear Equations': q => q.question.includes('slope') ? 'In y = mx + b, the slope is m (the number before x).' : 'Plug in the x value and calculate.',
  'Exponents & Roots': q => q.question.includes('√') ? 'What number multiplied by itself gives this?' : 'Multiply the base by itself, the exponent number of times.',
  'Pythagorean Theorem': () => 'a² + b² = c². The longest side is always c (hypotenuse).',
  'Quadratic Equations': () => 'Find two numbers that multiply to c and add to b.',
  'Quadratics': () => 'Find two numbers that multiply to c and add to b.',
  'Polynomials': () => 'Combine like terms: add the x-coefficients, then add the constants.',
  'Inequalities': () => 'Solve like an equation, then find the largest integer that works.',
  'Trigonometry': () => 'SOH-CAH-TOA: Sin = Opposite/Hypotenuse, Cos = Adjacent/Hypotenuse, Tan = Opposite/Adjacent.',
  'Trigonometric Functions': () => 'SOH-CAH-TOA: Sin = Opposite/Hypotenuse, Cos = Adjacent/Hypotenuse, Tan = Opposite/Adjacent.',
  'Systems of Equations': () => 'Plug in the known value and solve for the unknown.',
  'Sequences & Series': q => q.question.includes('Arithmetic') ? 'nth term = first + (n-1) × difference.' : 'nth term = first × ratio^(n-1).',
  'Financial Math': () => 'Simple Interest = Principal × Rate × Time ÷ 100.',
  'Limits & Derivatives': () => 'Plug the value directly into the expression.',
  'Vectors': q => q.question.includes('Add') ? 'Add each component separately: (x₁+x₂, y₁+y₂).' : 'Dot product: multiply matching components, then add.',
};

// ── Steps generator ─────────────────────────────────────────────────────
function generateSteps(q) {
  const text = q.question;
  const ans = q.answer;
  // Parse common patterns
  const addMatch = text.match(/(\d+\.?\d*)\s*\+\s*(\d+\.?\d*)/);
  if (addMatch) return [`Step 1: ${addMatch[1]} + ${addMatch[2]}`, `Step 2: Calculate the sum = ${ans}`];
  const subMatch = text.match(/(\d+\.?\d*)\s*[−\-]\s*(\d+\.?\d*)/);
  if (subMatch) return [`Step 1: ${subMatch[1]} − ${subMatch[2]}`, `Step 2: Calculate the difference = ${ans}`];
  const mulMatch = text.match(/(\d+\.?\d*)\s*[×x]\s*(\d+\.?\d*)/);
  if (mulMatch) return [`Step 1: ${mulMatch[1]} × ${mulMatch[2]}`, `Step 2: Calculate the product = ${ans}`];
  const divMatch = text.match(/(\d+\.?\d*)\s*÷\s*(\d+\.?\d*)/);
  if (divMatch) return [`Step 1: ${divMatch[1]} ÷ ${divMatch[2]}`, `Step 2: Calculate the quotient = ${ans}`];
  const eqMatch = text.match(/Solve/i);
  if (eqMatch) return [`Step 1: Isolate the variable`, `Step 2: The answer is ${ans}`];
  return [`Step 1: Read the problem carefully`, `Step 2: The answer is ${ans}`];
}

// ── French translation helper ───────────────────────────────────────────
function translateToFrench(question) {
  return question
    .replace(/What is/gi, 'Quel est')
    .replace(/What comes next\?/gi, 'Quel est le prochain nombre ?')
    .replace(/How many sides does a/gi, 'Combien de côtés a un')
    .replace(/How many/gi, 'Combien')
    .replace(/How much is/gi, 'Combien font')
    .replace(/Which shape has/gi, 'Quelle forme a')
    .replace(/Which is longer\?/gi, 'Lequel est plus long ?')
    .replace(/Find the mean/gi, 'Trouvez la moyenne')
    .replace(/Find the median/gi, 'Trouvez la médiane')
    .replace(/Find one root/gi, 'Trouvez une racine')
    .replace(/Find/gi, 'Trouvez')
    .replace(/Solve/gi, 'Résolvez')
    .replace(/Simplify/gi, 'Simplifiez')
    .replace(/Compare/gi, 'Comparez')
    .replace(/Add vectors/gi, 'Additionnez les vecteurs')
    .replace(/Dot product/gi, 'Produit scalaire')
    .replace(/A box is/gi, 'Une boîte mesure')
    .replace(/volume/gi, 'le volume')
    .replace(/Area of a rectangle/gi, 'Aire d\'un rectangle')
    .replace(/Area of a triangle/gi, 'Aire d\'un triangle')
    .replace(/Right triangle/gi, 'Triangle rectangle')
    .replace(/A bag has/gi, 'Un sac contient')
    .replace(/are red/gi, 'sont rouges')
    .replace(/probability of picking red/gi, 'probabilité de choisir une rouge')
    .replace(/A clock shows/gi, 'Une horloge affiche')
    .replace(/What hour is it\?/gi, 'Quelle heure est-il ?')
    .replace(/the tens digit/gi, 'le chiffre des dizaines')
    .replace(/the ones digit/gi, 'le chiffre des unités')
    .replace(/the hundreds digit/gi, 'le chiffre des centaines')
    .replace(/sides/gi, 'côtés')
    .replace(/length/gi, 'longueur')
    .replace(/width/gi, 'largeur')
    .replace(/height/gi, 'hauteur')
    .replace(/base/gi, 'base')
    .replace(/Largest integer/gi, 'Plus grand entier')
    .replace(/first/gi, 'premier')
    .replace(/common difference/gi, 'raison')
    .replace(/term/gi, 'terme')
    .replace(/items? cost/gi, 'articles coûtent')
    .replace(/If 1 item costs/gi, 'Si 1 article coûte')
    .replace(/Simple interest/gi, 'Intérêt simple')
    .replace(/years/gi, 'ans')
    .replace(/Interest earned\?/gi, 'Intérêt gagné ?')
    .replace(/Sum of roots\?/gi, 'Somme des racines ?')
    .replace(/Factor/gi, 'Factorisez')
    .replace(/slope/gi, 'la pente')
    .replace(/ of /g, ' de ')
    .replace(/\?$/, ' ?');
}

function generateQuestion(grade, topic, difficulty) {
  const gen = GENERATORS[topic];
  if (!gen) return genAddSub(grade, difficulty);
  const q = gen(grade, difficulty);
  // Attach hint
  const hintFn = HINTS[topic];
  q.hint = hintFn ? hintFn(q) : 'Think carefully about the problem.';
  // Attach steps
  q.steps = generateSteps(q);
  // Attach French translation
  q.questionFr = translateToFrench(q.question);
  return q;
}

function generateQuiz(grade, topics, difficulty, count) {
  const questions = [];
  for (let i = 0; i < count; i++) {
    const topic = topics.length > 0 ? topics[i % topics.length] : pick(getTopicsForGrade(grade));
    questions.push({ ...generateQuestion(grade, topic, difficulty), topic });
  }
  return shuffle(questions);
}
