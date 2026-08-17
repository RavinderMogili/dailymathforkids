'use strict';

// Canonical Phase 0 question quality twin.  Keep arithmetic in BigInt-backed
// rationals; Number is used only when emitting small fixture integers.

const PLACEHOLDERS = new Set(['todo', 'tbd', 'undefined', 'nan', 'null', 'infinity']);
const UNITS = ['degC', 'cm2', 'cm3', 'm2', 'm3', 'mL', 'km', 'mm', 'kg', 'cm', 'deg', 'min', 'h', 's', 'L', 'm', 'g'];
const UNIT_DIMENSION = {
  mm: 'length', cm: 'length', m: 'length', km: 'length',
  cm2: 'area', m2: 'area', cm3: 'volume', m3: 'volume',
  g: 'mass', kg: 'mass', mL: 'capacity', L: 'capacity',
  deg: 'angle', degC: 'temperature', min: 'time', h: 'time', s: 'time',
};
const UNIT_FACTORS = {
  mm: R(1n, 1000n), cm: R(1n, 100n), m: R(1n), km: R(1000n),
  g: R(1n), kg: R(1000n), mL: R(1n), L: R(1000n),
  s: R(1n), min: R(60n), h: R(3600n),
};

function abs(x) { return x < 0n ? -x : x; }
function gcd(a, b) {
  a = abs(a); b = abs(b);
  while (b) { const t = a % b; a = b; b = t; }
  return a || 1n;
}
function R(n, d = 1n) {
  if (d === 0n) throw new Error('ZERO_DENOMINATOR');
  if (d < 0n) { n = -n; d = -d; }
  const g = gcd(n, d);
  return { n: n / g, d: d / g };
}
function add(a, b) { return R(a.n * b.d + b.n * a.d, a.d * b.d); }
function sub(a, b) { return R(a.n * b.d - b.n * a.d, a.d * b.d); }
function mul(a, b) { return R(a.n * b.n, a.d * b.d); }
function div(a, b) { return R(a.n * b.d, a.d * b.n); }
function cmp(a, b) { const x = a.n * b.d, y = b.n * a.d; return x < y ? -1 : x > y ? 1 : 0; }
function eqR(a, b) { return a.n === b.n && a.d === b.d; }
function integerSqrt(value) {
  if (value < 0n) return null;
  if (value < 2n) return value;
  let low = 1n, high = value;
  while (low <= high) {
    const middle = (low + high) / 2n;
    const square = middle * middle;
    if (square === value) return middle;
    if (square < value) low = middle + 1n;
    else high = middle - 1n;
  }
  return null;
}
function roundRational(value, decimals) {
  const factor = 10n ** BigInt(decimals);
  let scaledNumerator = value.n * factor;
  const negative = scaledNumerator < 0n;
  if (negative) scaledNumerator = -scaledNumerator;
  let quotient = scaledNumerator / value.d;
  const remainder = scaledNumerator % value.d;
  if (remainder * 2n >= value.d) quotient += 1n;
  if (negative) quotient = -quotient;
  return R(quotient, factor);
}
function asInt(value) {
  const n = Number(value);
  return Number.isSafeInteger(n) ? n : value.toString();
}
function canonicalNumber(kind, value, extra = {}) {
  return { kind, num: asInt(value.n), den: asInt(value.d), ...extra };
}
function textValue(value) { return { kind: 'text', value: value.toLocaleLowerCase('en').trim().split(/\s+/).join(' ') }; }
function normalText(value) {
  return String(value == null ? '' : value).normalize('NFKC')
    .replace(/\u00a0/g, ' ').replace(/[²]/g, '2').replace(/[³]/g, '3').replace(/°/g, 'deg')
    .replace(/[−–—]/g, '-').replace(/×/g, '*').replace(/÷/g, '/')
    .trim().split(/\s+/).join(' ');
}
function placeholder(text) {
  const lowered = text.toLocaleLowerCase('en').trim();
  if (!lowered) return 'MISSING_FIELD';
  if (lowered.includes('___') || PLACEHOLDERS.has(lowered)) return 'PLACEHOLDER_TEXT';
  return null;
}
function parseNumber(raw) {
  const text = raw.replace(/,/g, '').trim();
  let m = text.match(/^([+-]?\d+)\s+(\d+)\/(\d+)$/);
  if (m) {
    const whole = BigInt(m[1]), numerator = BigInt(m[2]), denominator = BigInt(m[3]);
    if (!denominator) return [null, {}, 'ZERO_DENOMINATOR'];
    const sign = whole < 0n ? -1n : 1n;
    const value = add(R(whole), R(sign * numerator, denominator));
    return [value, { written_num: asInt(value.n), written_den: asInt(value.d), mixed: true }, null];
  }
  m = text.match(/^([+-]?\d+)\/(\d+)$/);
  if (m) {
    const numerator = BigInt(m[1]), denominator = BigInt(m[2]);
    if (!denominator) return [null, {}, 'ZERO_DENOMINATOR'];
    return [R(numerator, denominator), { written_num: asInt(numerator), written_den: asInt(denominator) }, null];
  }
  m = text.match(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/);
  if (m) {
    const sign = text.startsWith('-') ? -1n : 1n;
    const unsigned = text.replace(/^[+-]/, '');
    if (unsigned.includes('.')) {
      const [whole, places] = unsigned.split('.');
      return [R(sign * BigInt((whole || '0') + places), 10n ** BigInt(places.length)),
        { written_decimals: places.length }, null];
    }
    return [R(sign * BigInt(unsigned)), {}, null];
  }
  return [null, {}, 'PARSE_FAILED'];
}
function parseValue(raw) {
  const text = normalText(raw);
  const bad = placeholder(text);
  if (bad) return [null, bad];
  let m = text.match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$/i);
  if (m) {
    let hour = Number(m[1]), minute = Number(m[2] || 0);
    if (hour >= 1 && hour <= 12 && minute < 60) {
      if (hour === 12) hour = 0;
      return [{ kind: 'time', minutes: hour * 60 + minute, meridiem: m[3].toUpperCase() }, null];
    }
  }
  m = text.match(/^(\d{1,2}):(\d{1,2})$/);
  if (m) {
    const hour = Number(m[1]), minute = Number(m[2]);
    if (minute < 60 && (m[2].length === 2 || minute === 0) && hour >= 0 && hour <= 23) {
      return [{ kind: 'time', minutes: hour * 60 + minute, meridiem: null }, null];
    }
  }
  m = text.match(/^([+-]?\d+)\s*(?:R|remainder)\s*([+-]?\d+)$/i);
  if (m) return [{ kind: 'quotrem', q: Number(m[1]), r: Number(m[2]) }, null];
  if (/^[+-]?\d+(?::[+-]?\d+)+$/.test(text)) {
    const terms = text.split(':').map(Number);
    let divisor = 0;
    terms.forEach(term => { divisor = Number(gcd(BigInt(divisor), BigInt(term))); });
    divisor ||= 1;
    return [{ kind: 'ratio', terms: terms.map(term => term / divisor) }, null];
  }
  m = text.match(/^(.+?)\s*%$/);
  if (m) {
    const [value, meta, code] = parseNumber(m[1]);
    if (code === 'ZERO_DENOMINATOR') return [null, code];
    if (!code) return [canonicalNumber('percent', value, meta), null];
  }
  m = text.match(/^(?:\$|A\$)\s*(.+)$/i) || text.match(/^(.+?)\s*(?:\$|dollars?)$/i);
  if (m) {
    const [value, meta, code] = parseNumber(m[1]);
    if (code === 'ZERO_DENOMINATOR') return [null, code];
    if (!code) return [canonicalNumber('currency', value, { symbol: '$', ...meta }), null];
  }
  m = text.match(/^(.+?)\s*(?:¢|cents?)$/i);
  if (m) {
    const [value, meta, code] = parseNumber(m[1]);
    if (code === 'ZERO_DENOMINATOR') return [null, code];
    if (!code) return [canonicalNumber('currency', value, { symbol: '¢', ...meta }), null];
  }
  const unitPattern = UNITS.slice().sort((a, b) => b.length - a.length).map(x => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  m = text.match(new RegExp(`^(.+?)\\s*(${unitPattern})$`));
  if (m) {
    const [value, meta, code] = parseNumber(m[1]);
    if (code === 'ZERO_DENOMINATOR') return [null, code];
    if (!code) return [canonicalNumber('measurement', value, { unit: m[2], ...meta }), null];
  }
  const [value, meta, code] = parseNumber(text);
  if (!code) return [canonicalNumber('number', value, meta), null];
  if (code !== 'PARSE_FAILED') return [null, code];
  return [textValue(text), null];
}
function serializeValue(value, code) {
  if (!value) return { status: 'PARSE_FAILED', code: code || 'PARSE_FAILED' };
  const result = { ...value };
  delete result.mixed;
  return result;
}
function valuesEqual(a, b) {
  if (!a || !b) return [false, 'PARSE_FAILED'];
  const ka = a.kind, kb = b.kind;
  if ((ka === 'currency') !== (kb === 'currency')) return [false, 'UNIT_ASSERTION'];
  if (['number', 'percent', 'currency'].includes(ka) && ['number', 'percent', 'currency'].includes(kb)) {
    if (ka !== kb) return [false, 'VALUE_CHANGED'];
    if (ka === 'currency' && a.symbol !== b.symbol) return [false, 'VALUE_CHANGED'];
    const same = a.num === b.num && a.den === b.den;
    return [same, same ? null : 'VALUE_CHANGED'];
  }
  if (ka === 'measurement' && kb === 'measurement') {
    const same = a.num === b.num && a.den === b.den && a.unit === b.unit;
    return [same, same || a.unit === b.unit ? null : 'UNIT_MISMATCH'];
  }
  if ((ka === 'number' && kb === 'measurement') || (ka === 'measurement' && kb === 'number')) return [false, 'UNIT_ASSERTION'];
  if (ka === 'time' && kb === 'time') {
    const same = a.minutes === b.minutes && a.meridiem === b.meridiem;
    return [same, same ? null : 'VALUE_CHANGED'];
  }
  if (ka === 'ratio' && kb === 'ratio') {
    const same = JSON.stringify(a.terms) === JSON.stringify(b.terms);
    return [same, same ? null : 'VALUE_CHANGED'];
  }
  if (ka === 'quotrem' && kb === 'quotrem') {
    const same = a.q === b.q && a.r === b.r;
    return [same, same ? null : 'VALUE_CHANGED'];
  }
  if (ka === 'text' && kb === 'text') {
    const same = a.value === b.value;
    return [same, same ? null : 'VALUE_CHANGED'];
  }
  return [false, 'VALUE_CHANGED'];
}
function equivalentStrings(a, b) {
  const [va, ca] = parseValue(a), [vb, cb] = parseValue(b);
  if (!va || !vb) return [false, ca || cb || 'PARSE_FAILED'];
  return valuesEqual(va, vb);
}

function tokenizeExpression(text) {
  const source = text.replace(/,/g, '');
  const tokens = [];
  let pos = 0;
  const re = /\s*(\d+(?:\.\d+)?(?:\/\d+)?|[()+\-*/])/y;
  while (pos < source.length) {
    re.lastIndex = pos;
    const match = re.exec(source);
    if (!match) return null;
    tokens.push(match[1]); pos = re.lastIndex;
  }
  return tokens;
}
function evalExpression(text) {
  const tokens = tokenizeExpression(text);
  if (!tokens || !tokens.length) return null;
  let index = 0;
  function atom() {
    if (index >= tokens.length) return null;
    if (tokens[index] === '+' || tokens[index] === '-') {
      const sign = tokens[index++] === '-' ? -1n : 1n;
      const value = atom(); return value ? R(sign * value.n, value.d) : null;
    }
    if (tokens[index] === '(') {
      index++; const value = expr();
      if (tokens[index] !== ')') return null;
      index++; return value;
    }
    const [value, , code] = parseNumber(tokens[index++]);
    return code ? null : value;
  }
  function term() {
    let value = atom();
    while (value && index < tokens.length && ['*', '/'].includes(tokens[index])) {
      const op = tokens[index++], right = atom();
      if (!right || (op === '/' && right.n === 0n)) return null;
      value = op === '*' ? mul(value, right) : div(value, right);
    }
    return value;
  }
  function expr() {
    let value = term();
    while (value && index < tokens.length && ['+', '-'].includes(tokens[index])) {
      const op = tokens[index++], right = term();
      if (!right) return null;
      value = op === '+' ? add(value, right) : sub(value, right);
    }
    return value;
  }
  const value = expr();
  return index === tokens.length ? value : null;
}
function numberValue(value) { return canonicalNumber('number', value); }
function textCanonical(value) { return textValue(value); }
function solveQuestion(question) {
  const text = normalText(question), lowered = text.toLocaleLowerCase('en');
  let m = text.match(/compare:\s*([-+]?\d+(?:\.\d+)?(?:\/\d+)?)\s+_{2,}\s*([-+]?\d+(?:\.\d+)?(?:\/\d+)?)/i);
  if (m) {
    const [a] = parseNumber(m[1]), [b] = parseNumber(m[2]);
    return [textCanonical(cmp(a, b) === 0 ? '=' : cmp(a, b) > 0 ? '>' : '<'), null];
  }
  m = lowered.match(/which is the (largest|smallest)\?\s*(.*)$/);
  if (m) {
    const values = [...m[2].matchAll(/[-+]?\d+(?:\.\d+)?/g)].map(x => R(BigInt(x[0].replace('.', '')), 10n ** BigInt((x[0].split('.')[1] || '').length)));
    if (values.length) {
      const target = values.reduce((best, value) => (m[1] === 'largest' ? (cmp(value, best) > 0 ? value : best) : (cmp(value, best) < 0 ? value : best)), values[0]);
      if (values.filter(value => eqR(value, target)).length > 1) return [null, 'TIED_EXTREME_IN_LIST'];
      return [numberValue(target), null];
    }
  }
  m = lowered.match(/(?:a|an)\s+([a-z][\w -]*)\s+is\s+([-+]?\d+(?:\.\d+)?)\s*([a-z0-9]+).*?(?:a|an)\s+([a-z][\w -]*)\s+is\s+([-+]?\d+(?:\.\d+)?)\s*([a-z0-9]+).*?which is (longer|larger|shorter|smaller)/);
  if (m) {
    const [, first, n1, u1, second, n2, u2, relation] = m;
    if (u1 !== u2) return [null, 'UNVERIFIED'];
    const a = R(BigInt(n1.replace('.', '')), 10n ** BigInt((n1.split('.')[1] || '').length));
    const b = R(BigInt(n2.replace('.', '')), 10n ** BigInt((n2.split('.')[1] || '').length));
    if (eqR(a, b)) return [null, 'TIED_OPERANDS'];
    const firstWins = (['longer', 'larger'].includes(relation) && cmp(a, b) > 0) || (['shorter', 'smaller'].includes(relation) && cmp(a, b) < 0);
    return [textCanonical(firstWins ? first : second), null];
  }
  m = lowered.match(/original price:\s*\$?\s*([-+]?\d+(?:\.\d+)?).*?sale price:\s*\$?\s*([-+]?\d+(?:\.\d+)?)/);
  if (m) {
    const original = R(BigInt(m[1].replace('.', '')), 10n ** BigInt((m[1].split('.')[1] || '').length));
    const sale = R(BigInt(m[2].replace('.', '')), 10n ** BigInt((m[2].split('.')[1] || '').length));
    if (cmp(sale, original) >= 0) return [null, 'SALE_PRICE_GE_ORIGINAL'];
    return [canonicalNumber('percent', div(mul(sub(original, sale), R(100n)), original)), null];
  }
  m = text.match(/([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|km|g|kg|mL|L)\s*(?:=|to)\s*(?:\?|how many)?\s*(mm|cm|m|km|g|kg|mL|L)/i);
  if (m) {
    const [amount] = parseNumber(m[1]);
    const source = UNITS.find(u => u.toLowerCase() === m[2].toLowerCase()) || m[2];
    const target = UNITS.find(u => u.toLowerCase() === m[3].toLowerCase()) || m[3];
    if (UNIT_DIMENSION[source] !== UNIT_DIMENSION[target]) return [null, 'UNVERIFIED'];
    return [canonicalNumber('measurement', div(mul(amount, UNIT_FACTORS[source]), UNIT_FACTORS[target]), { unit: target }), null];
  }
  m = lowered.match(/square has a side of\s+([\d.]+)\s*cm.*?perimeter/);
  if (m) { const [v] = parseNumber(m[1]); return [canonicalNumber('measurement', mul(v, R(4n)), { unit: 'cm' }), null]; }
  m = lowered.match(/rectangle.*?([\d.]+)\s*cm\s+long.*?([\d.]+)\s*cm\s+wide.*?perimeter/);
  if (m) { const [a] = parseNumber(m[1]), [b] = parseNumber(m[2]); return [canonicalNumber('measurement', mul(add(a, b), R(2n)), { unit: 'cm' }), null]; }
  m = lowered.match(/area of a rectangle:\s*length\s*=\s*([\d.]+).*?width\s*=\s*([\d.]+)/);
  if (m) { const [a] = parseNumber(m[1]), [b] = parseNumber(m[2]); return [numberValue(mul(a, b)), null]; }
  m = lowered.match(/(?:box is|volume of a rectangular prism).*?([\d.]+)\s*[x*]\s*([\d.]+)\s*[x*]\s*([\d.]+)/);
  if (m) { const [a] = parseNumber(m[1]), [b] = parseNumber(m[2]), [c] = parseNumber(m[3]); return [numberValue(mul(mul(a, b), c)), null]; }
  m = lowered.match(/(?:from|start:)\s*(\d{1,2}):(\d{2}).*?(?:to|end:)\s*(\d{1,2}):(\d{2}).*?minutes/);
  if (m) return [numberValue(R(BigInt((Number(m[3]) * 60 + Number(m[4])) - (Number(m[1]) * 60 + Number(m[2])))), null), null];
  m = lowered.match(/starts at (\d{1,2}):00 and ends at (\d{1,2}):00.*?hours/);
  if (m) return [numberValue(R(BigInt(Number(m[2]) - Number(m[1])))), null];
  m = lowered.match(/if\s+y\s*=\s*([-+]?\d+(?:\.\d+)?)\s*x\s*([+-])\s*(\d+(?:\.\d+)?).*?x\s*=\s*([-+]?\d+(?:\.\d+)?).*?what is y/);
  if (m) {
    const [slope] = parseNumber(m[1]), [intercept] = parseNumber(m[3]), [x] = parseNumber(m[4]);
    return [numberValue(add(mul(slope, x), m[2] === '+' ? intercept : R(-intercept.n, intercept.d))), null];
  }
  m = text.match(/(\d+)\^(\d+)\s*[×x*]\s*\1\^(\d+)\s*=\s*\1\^\?/);
  if (m) return [numberValue(R(BigInt(Number(m[2]) + Number(m[3])))), null];
  m = text.match(/([-+]?\d+)\s*\^\s*([-+]?\d+)/);
  if (m) return [numberValue(R(BigInt(m[1]) ** BigInt(m[2]))), null];
  m = text.match(/(?:\u221a|sqrt\(?\s*)(\d+)/i);
  if (m) { const root = integerSqrt(BigInt(m[1])); if (root != null) return [numberValue(R(root)), null]; }
  m = text.match(/(?:what is\s+)?([-+]?\d+\/\d+)\s*([+\-x*÷\/])\s*([-+]?\d+\/\d+)/i);
  if (m) {
    const [left] = parseNumber(m[1]), [right] = parseNumber(m[3]);
    if (!left || !right || ((m[2] === '÷' || m[2] === '/') && right.n === 0n)) return [null, 'UNVERIFIED'];
    const value = m[2] === '+' ? add(left, right)
      : m[2] === '-' ? sub(left, right)
      : m[2] === 'x' || m[2] === '*' ? mul(left, right)
      : div(left, right);
    return [numberValue(value), null];
  }
  m = text.match(/([-+]?\d+)\s*(?:÷|\/)\s*([-+]?\d+)\s*=\s*\?/);
  if (m) {
    const dividend = Number(m[1]), divisor = Number(m[2]);
    if (divisor) {
      const quotient = Math.floor(dividend / divisor), remainder = dividend % divisor;
      if (remainder === 0) return [numberValue(R(BigInt(quotient))), null];
      return [{ kind: 'quotrem', q: quotient, r: remainder }, null];
    }
  }
  m = text.match(/(\d+)\^(\d+)\s*[×x*]\s*\1\^(\d+)\s*=\s*\1\^\?/);
  if (m) return [numberValue(R(BigInt(Number(m[2]) + Number(m[3])))), null];
  m = text.match(/Dot product:\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*[·.]\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*=\s*\?/i);
  if (m) {
    const value = Number(m[1]) * Number(m[3]) + Number(m[2]) * Number(m[4]);
    return [numberValue(R(BigInt(value))), null];
  }
  m = text.match(/([-+*/()\d.,\s]+?)\s*=\s*\?/);
  if (m && /[+\-*/]/.test(m[1])) {
    const value = evalExpression(m[1].replace(/×/g, '*').replace(/÷/g, '/'));
    if (value) return [numberValue(value), null];
  }
  m = lowered.match(/what is\s+([-+]?\d+(?:\.\d+)?)\s*%\s+of\s+([-+]?\d+(?:\.\d+)?)/);
  if (m) { const [a] = parseNumber(m[1]), [b] = parseNumber(m[2]); return [numberValue(div(mul(a, b), R(100n))), null]; }
  m = lowered.match(/([-+]?\d+)\s*(?:÷|\/)\s*([-+]?\d+).*(?:remainder|with remainder)/);
  if (m) { const a = Number(m[1]), b = Number(m[2]); if (b) return [{ kind: 'quotrem', q: Math.floor(a / b), r: a % b }, null]; }
  return [null, 'UNVERIFIED'];
}
function fractionIssues(value, grade) {
  if (!value || value.kind !== 'number' || value.written_den == null) return [];
  const n = BigInt(value.written_num), d = BigInt(value.written_den), issues = [];
  if (gcd(n, d) !== 1n) issues.push('FRACTION_NOT_LOWEST_TERMS');
  if (BigInt(value.den) === 1n) issues.push('FRACTION_DENOMINATOR_ONE');
  if (Number(grade) <= 4 && abs(n) > d && !value.mixed) issues.push('IMPROPER_FRACTION_FOR_GRADE');
  return issues;
}
function validateQuestion(question, options = {}) {
  const gradeRaw = question.grade == null ? '' : question.grade;
  const match = String(gradeRaw).match(/\d+/), grade = match ? Number(match[0]) : 0;
  const index = Number(question.num || question.question_index || 0);
  const text = String(question.question || question.en || '').trim();
  const answer = question.answer;
  const choices = question.choices || [];
  const codes = [];
  const addCode = code => { if (code && !codes.includes(code)) codes.push(code); };
  if (!text || answer == null || String(answer).trim() === '' || !choices.length) {
    addCode('MISSING_FIELD');
    return { verdict: 'ERROR', codes, grade: gradeRaw, question_index: index };
  }
  if (options.require_french && !String(question.fr || '').trim()) addCode('MISSING_FRENCH');
  if (Number(question.answer_line_count || 1) > 1) addCode('MULTIPLE_ANSWER_LINES');
  const allText = ['title', 'en', 'fr', 'hint', 'answer', 'choices_raw'].map(key => String(question[key] || '')).join(' ');
  if (/\+\s*-|-\s*-|\+-/.test(allText)) addCode('MALFORMED_SIGN');
  if (/\b(?:TODO|TBD|undefined|NaN|null|Infinity)\b/i.test(allText)) addCode('PLACEHOLDER_TEXT');
  if (choices.length !== 4) addCode('CHOICE_COUNT');
  const parsedChoices = choices.map(choice => parseValue(choice)), answerParsed = parseValue(answer);
  const choiceValues = parsedChoices.map(item => item[0]), choiceErrors = parsedChoices.map(item => item[1]);
  const [answerValue, answerError] = answerParsed;
  const fractionCodes = [];
  [answerValue, ...choiceValues].forEach(value => fractionIssues(value, grade).forEach(code => { if (!fractionCodes.includes(code)) fractionCodes.push(code); }));
  if (answerValue && answerValue.written_den != null && (answerValue.den === 1 || Math.abs(answerValue.written_num) > answerValue.written_den)) {
    while (fractionCodes.includes('FRACTION_NOT_LOWEST_TERMS')) fractionCodes.splice(fractionCodes.indexOf('FRACTION_NOT_LOWEST_TERMS'), 1);
  }
  fractionCodes.forEach(addCode);
  if ([answerError, ...choiceErrors].includes('ZERO_DENOMINATOR')) addCode('ZERO_DENOMINATOR');
  const divisor = text.match(/(?:÷|\/)\s*(\d+).*(?:remainder|with remainder)/i);
  if (divisor) choiceValues.forEach(value => { if (value && value.kind === 'quotrem' && !(value.r >= 0 && value.r < Number(divisor[1]))) addCode('REMAINDER_GE_DIVISOR'); });
  const answerFormatException = Boolean(answerValue && answerValue.written_den != null && (answerValue.den === 1 || Math.abs(answerValue.written_num) > answerValue.written_den));
  if (choices.length === 4 && !fractionCodes.includes('FRACTION_NOT_LOWEST_TERMS') && !answerFormatException) {
    for (let i = 0; i < choiceValues.length; i++) for (let j = i + 1; j < choiceValues.length; j++) {
      if (valuesEqual(choiceValues[i], choiceValues[j])[0]) addCode('DUPLICATE_CHOICES');
    }
    const normalized = choices.map(normalText).map(x => x.toLocaleLowerCase('en'));
    for (let i = 0; i < normalized.length; i++) for (let j = 0; j < normalized.length; j++) {
      const numericPair = choiceValues[i] && choiceValues[j] && choiceValues[i].kind === 'number' && choiceValues[j].kind === 'number';
      if (i !== j && !numericPair && normalized[j].startsWith(normalized[i]) && normalized[i] !== normalized[j]) addCode('CHOICE_IS_PREFIX_OF_CHOICE');
    }
  }
  const matches = [], mismatchCodes = [];
  if (answerValue) choiceValues.forEach((choiceValue, i) => {
    const [same, mismatch] = valuesEqual(answerValue, choiceValue);
    if (same) matches.push(i); else if (mismatch) mismatchCodes.push(mismatch);
  });
  if (!matches.length) addCode(mismatchCodes.includes('UNIT_ASSERTION') ? 'UNIT_ASSERTION' : 'NO_CORRECT_OPTION');
  const extreme = text.match(/which is the (?:largest|smallest)\?\s*(.*)$/i);
  const extremeNumbers = extreme ? [...extreme[1].matchAll(/[-+]?\d+(?:\.\d+)?/g)].map(item => item[0]) : [];
  const tiedExtreme = extremeNumbers.length !== new Set(extremeNumbers).size;
  if (matches.length > 1 && !tiedExtreme) addCode('MULTIPLE_CORRECT_OPTIONS');
  if (/\b(percent off|discount)\b/i.test(text)) {
    const sale = text.match(/original price:\s*\$?\s*([\d.]+).*?sale price:\s*\$?\s*([\d.]+)/i);
    if (sale && cmp(parseNumber(sale[2])[0], parseNumber(sale[1])[0]) >= 0) addCode('SALE_PRICE_GE_ORIGINAL');
    if (answerValue && answerValue.kind === 'percent') {
      if (BigInt(answerValue.num) <= 0n) addCode('NEGATIVE_PERCENT_OFF');
      else if (BigInt(answerValue.num) >= 100n * BigInt(answerValue.den)) addCode('PERCENT_OUT_OF_RANGE');
    }
  }
  const [solved, solveCode] = solveQuestion(text);
  const compare = text.match(/compare:\s*([-+]?\d+(?:\.\d+)?(?:\/\d+)?)\s+_{2,}\s*([-+]?\d+(?:\.\d+)?(?:\/\d+)?)/i);
  if (compare) {
    const [left] = parseValue(compare[1]), [right] = parseValue(compare[2]);
    if (left && right && BigInt(left.num) * BigInt(right.den) === BigInt(right.num) * BigInt(left.den)) addCode('EQUAL_OPERANDS_COMPARISON');
  }
  if (solveCode === 'TIED_OPERANDS') addCode('TIED_OPERANDS');
  if (solveCode === 'TIED_EXTREME_IN_LIST') addCode('TIED_EXTREME_IN_LIST');
  if (solveCode === 'SALE_PRICE_GE_ORIGINAL') addCode('SALE_PRICE_GE_ORIGINAL');
  const arithmeticResult = /^\s*[-+]?\d+(?:\.\d+)?\s*[x*\u00d7\u00f7/]\s*[-+]?\d+(?:\.\d+)?\s*=\s*\?\s*$/i.test(text);
  if (arithmeticResult && solved && answerValue && answerValue.kind === 'number') {
    const roundingInstruction = /\b(round|rounded|nearest|decimal places?)\b/i.test(text);
    const [same] = valuesEqual(answerValue, solved);
    if (!same && !roundingInstruction) addCode('UNROUNDED_WITHOUT_INSTRUCTION');
  }
  if (/which is the (largest|smallest)/i.test(text) && solved) {
    const extreme = text.toLocaleLowerCase('en').match(/which is the (largest|smallest)\?\s*(.*)$/);
    if (extreme) {
      const values = [...extreme[2].matchAll(/[-+]?\d+(?:\.\d+)?/g)].map(x => parseNumber(x[0])[0]);
      const target = values.reduce((best, value) => extreme[1] === 'largest' ? (cmp(value, best) > 0 ? value : best) : (cmp(value, best) < 0 ? value : best), values[0]);
      choiceValues.forEach(value => {
        if (value && value.kind === 'number') {
          const candidate = R(BigInt(value.num), BigInt(value.den));
          if ((extreme[1] === 'largest' && cmp(candidate, target) > 0) || (extreme[1] === 'smallest' && cmp(candidate, target) < 0)) addCode('DISTRACTOR_BEATS_ANSWER');
        }
      });
    }
  }
  if (answerValue && solved && !['TIED_OPERANDS', 'TIED_EXTREME_IN_LIST', 'SALE_PRICE_GE_ORIGINAL'].includes(solveCode) && !['EQUAL_OPERANDS_COMPARISON', 'REMAINDER_GE_DIVISOR', 'UNROUNDED_WITHOUT_INSTRUCTION'].some(code => codes.includes(code))) {
    const [same, mismatch] = valuesEqual(answerValue, solved);
    if (!same && !['UNIT_ASSERTION', 'UNIT_MISMATCH'].includes(mismatch)) {
      const rounding = text.match(/\bround(?:ed)?(?:\s+to)?\s+(\d+)\s+decimal places\b/i);
      if (rounding && answerValue.written_decimals != null) {
        if (!eqR(roundRational(R(BigInt(solved.num), BigInt(solved.den)), Number(rounding[1])), R(BigInt(answerValue.num), BigInt(answerValue.den)))) {
          addCode('SOLVER_DISAGREEMENT');
        }
      } else {
        addCode('SOLVER_DISAGREEMENT');
      }
    }
  } else if (!solved && solveCode === 'UNVERIFIED' && !codes.length) addCode('UNVERIFIED');
  if (answerValue && question.hint && normalText(question.hint).toLocaleLowerCase('en').includes(normalText(answer).toLocaleLowerCase('en'))) addCode('HINT_LEAKS_ANSWER');
  const blockingCodes = codes.filter(code => code !== 'HINT_LEAKS_ANSWER');
  const verdict = blockingCodes.length ? (blockingCodes.length === 1 && blockingCodes[0] === 'UNVERIFIED' ? 'UNVERIFIED' : 'ERROR') : 'VALID';
  return { verdict, codes, grade: gradeRaw, question_index: index };
}
function conformanceResult(fixtures) {
  return {
    version: fixtures.version,
    parse: fixtures.parse.map(item => { const [value, code] = parseValue(item.input); return { input: item.input, result: serializeValue(value, code) }; }),
    equivalence: fixtures.equivalence.map(item => { const [equal, code] = equivalentStrings(item.a, item.b); return { a: item.a, b: item.b, equal, code }; }),
    forbidden_fixes: fixtures.forbidden_fixes.map(item => { const [equal, code] = equivalentStrings(item.stored, item.substituted); return { file: item.file, stored: item.stored, substituted: item.substituted, verdict: 'ERROR', code: code || 'VALUE_CHANGED' }; }),
    questions: fixtures.questions.map(item => ({ id: item.id, ...validateQuestion({
      grade: item.grade, num: 1, question: item.question, en: item.question, fr: item.fr,
      choices: item.choices, answer: item.answer, hint: item.hint,
    }, { require_french: item.require_french === true || Object.prototype.hasOwnProperty.call(item, 'fr') }) })),
    bounded_termination: fixtures.bounded_termination.map(item => {
      const space = new Set(item.distractor_values.map(String));
      return { id: item.id, code: space.size - (space.has(String(item.correct)) ? 1 : 0) + 1 < item.required_choices ? 'INSUFFICIENT_DISTRACTOR_SPACE' : null, must_terminate: true };
    }),
  };
}

const questionQualityApi = {
  parseValue, serializeValue, valuesEqual, equivalentStrings, solveQuestion,
  validateQuestion, conformanceResult, normalText,
};
if (typeof module !== 'undefined' && module.exports) module.exports = questionQualityApi;
if (typeof window !== 'undefined') window.DMKQuestionQuality = questionQualityApi;
