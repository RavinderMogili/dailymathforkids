/**
 * Jest tests for the extended (curated external-dataset) word-problem pool
 * feature-flag, merge, and exposure-tracking logic in practice-engine.js.
 *
 * practice-engine.js is a plain browser global-scope script (no module
 * exports), so each test runs it fresh inside its own vm context to avoid
 * "already declared" clashes and state bleeding between tests.
 *
 * Run with: npm run test:unit
 */
const vm = require('vm');
const fs = require('fs');
const path = require('path');

const SOURCE = fs.readFileSync(path.join(__dirname, 'practice-engine.js'), 'utf8');

function freshLoad({ enabled = false, extendedPool = [], practicePool = [], hostname = 'localhost' } = {}) {
  const localStorageStore = {};
  const sandbox = {
    console,
    URLSearchParams,
    localStorage: {
      getItem: k => (k in localStorageStore ? localStorageStore[k] : null),
      setItem: (k, v) => { localStorageStore[k] = String(v); },
      removeItem: k => { delete localStorageStore[k]; },
    },
    window: {
      DMK_ROOT: './',
      location: { search: enabled ? '?enableExtendedPool=1' : '', hostname, protocol: 'http:' },
    },
    fetch: (url) => {
      if (url.includes('practice-pool-extended.json')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(extendedPool) });
      }
      if (url.includes('practice-pool.json')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(practicePool) });
      }
      return Promise.resolve({ ok: false });
    },
  };
  const context = vm.createContext(sandbox);
  vm.runInContext(SOURCE, context, { filename: 'practice-engine.js' });
  return context;
}

function makeExtRecord(id, grade, overrides = {}) {
  return {
    grade, topic: 'Word Problems',
    question: `Q ${id}`, questionFr: '', choices: ['1', '2', '3', '4'], answer: '1',
    hint: 'hint', steps: ['step'], _source: 'gsm8k', _sourceId: id,
    _difficulty: 'easy', _sourceTopic: 'Word Problems (general)',
    ...overrides,
  };
}

async function settle() {
  await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
}

describe('extended pool feature flag', () => {
  test('disabled by default: extended pool never contributes questions', async () => {
    const ctx = freshLoad({ enabled: false, extendedPool: [makeExtRecord('gsm8k-1', 4)] });
    expect(ctx.isExtendedPoolEnabled()).toBe(false);
    await settle();
    const pool = ctx.getPoolQuestions(4, []);
    expect(pool.some(q => q._sourceId === 'gsm8k-1')).toBe(false);
  });

  test('enabled via query param on localhost: extended pool contributes questions for its grade', async () => {
    const ctx = freshLoad({ enabled: true, extendedPool: [makeExtRecord('gsm8k-1', 4)], hostname: 'localhost' });
    expect(ctx.isExtendedPoolEnabled()).toBe(true);
    await settle();
    const pool = ctx.getPoolQuestions(4, []);
    expect(pool.some(q => q._sourceId === 'gsm8k-1')).toBe(true);
  });

  test('query param is IGNORED on a production-looking hostname — cannot self-enable on the live site', async () => {
    const ctx = freshLoad({
      enabled: true, extendedPool: [makeExtRecord('gsm8k-1', 4)],
      hostname: 'dailymathforkids.com',
    });
    expect(ctx.isExtendedPoolEnabled()).toBe(false);
    await settle();
    const pool = ctx.getPoolQuestions(4, []);
    expect(pool.some(q => q._sourceId === 'gsm8k-1')).toBe(false);
  });

  test('query param is ignored on any non-dev hostname, not just the known production domain', async () => {
    const ctx = freshLoad({
      enabled: true, extendedPool: [makeExtRecord('gsm8k-1', 4)],
      hostname: 'some-preview-deploy.example.com',
    });
    expect(ctx.isExtendedPoolEnabled()).toBe(false);
  });

  test('127.0.0.1 and a file:// preview both count as local dev', () => {
    const ctxIp = freshLoad({ enabled: true, hostname: '127.0.0.1' });
    expect(ctxIp.isExtendedPoolEnabled()).toBe(true);

    const sandbox = {
      console, URLSearchParams,
      localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
      window: { DMK_ROOT: './', location: { search: '?enableExtendedPool=1', hostname: '', protocol: 'file:' } },
      fetch: () => Promise.resolve({ ok: false }),
    };
    const ctxFile = vm.createContext(sandbox);
    vm.runInContext(SOURCE, ctxFile, { filename: 'practice-engine.js' });
    expect(ctxFile.isExtendedPoolEnabled()).toBe(true);
  });

  test('fallback: insufficient approved questions for a grade never blocks a quiz', async () => {
    // Only 1 extended question exists for grade 4, but a 10-question quiz is requested —
    // generateQuiz must still return exactly 10 questions (padded algorithmically).
    const ctx = freshLoad({ enabled: true, extendedPool: [makeExtRecord('gsm8k-1', 4)] });
    await settle();
    const quiz = ctx.generateQuiz(4, ['Word Problems'], 'easy', 10);
    expect(quiz.length).toBe(10);
  });

  test('exposure tracking: a question shown recently is not reselected while alternatives exist', async () => {
    const pool = [makeExtRecord('gsm8k-1', 4), makeExtRecord('gsm8k-2', 4)];
    const ctx = freshLoad({ enabled: true, extendedPool: pool });
    await settle();
    ctx.recordSeenExtendedIds(['gsm8k-1']);
    const remaining = ctx.preferUnseen(ctx.getPoolQuestions(4, []), 1);
    expect(remaining.some(q => q._sourceId === 'gsm8k-1')).toBe(false);
    expect(remaining.some(q => q._sourceId === 'gsm8k-2')).toBe(true);
  });

  test('exposure tracking never starves a quiz: reuses seen questions if nothing else is left', async () => {
    const ctx = freshLoad({ enabled: true, extendedPool: [makeExtRecord('gsm8k-1', 4)] });
    await settle();
    ctx.recordSeenExtendedIds(['gsm8k-1']);
    const remaining = ctx.preferUnseen(ctx.getPoolQuestions(4, []), 1);
    expect(remaining.some(q => q._sourceId === 'gsm8k-1')).toBe(true);
  });

  test('existing hand-curated pool (data/practice-pool.json) is unaffected by the flag', async () => {
    const chatgptQ = { grade: 4, topic: 'Word Problems', question: 'legacy', questionFr: '',
      choices: ['1', '2', '3', '4'], answer: '1', hint: 'h', steps: ['s'] };
    const ctx = freshLoad({ enabled: false, practicePool: [chatgptQ] });
    await settle();
    const pool = ctx.getPoolQuestions(4, []);
    expect(pool.some(q => q.question === 'legacy')).toBe(true);
  });

  test('exactly one correct choice per extended-pool question actually used in a quiz', async () => {
    const ctx = freshLoad({ enabled: true, extendedPool: [
      makeExtRecord('gsm8k-1', 4, { choices: ['5', '10', '15', '20'], answer: '10' }),
    ] });
    await settle();
    const quiz = ctx.generateQuiz(4, ['Word Problems'], 'easy', 1);
    const q = quiz.find(x => x._sourceId === 'gsm8k-1');
    expect(q).toBeDefined();
    const matches = q.choices.filter(c => c === q.answer);
    expect(matches.length).toBe(1);
  });

  test('difficulty filter: Word Problems quiz only uses pool questions matching the selected difficulty', async () => {
    const ctx = freshLoad({ enabled: true, extendedPool: [
      makeExtRecord('gsm8k-easy', 4, { _difficulty: 'easy' }),
      makeExtRecord('gsm8k-medium', 4, { _difficulty: 'medium' }),
      makeExtRecord('gsm8k-hard', 4, { _difficulty: 'hard' }),
    ] });
    await settle();
    // Ask for 3 hard word problems — the hard record should surface, not easy/medium.
    const quiz = ctx.generateQuiz(4, ['Word Problems'], 'hard', 3);
    expect(quiz.some(q => q._sourceId === 'gsm8k-hard')).toBe(true);
    expect(quiz.some(q => q._sourceId === 'gsm8k-easy')).toBe(false);
    expect(quiz.some(q => q._sourceId === 'gsm8k-medium')).toBe(false);
    // Returned pool question carries both _difficulty and _sourceTopic forward.
    const used = quiz.find(q => q._sourceId === 'gsm8k-hard');
    expect(used._difficulty).toBe('hard');
    expect(used._sourceTopic).toBe('Word Problems (general)');
  });

  test('difficulty filter: mixed-topic quiz still respects difficulty for pooled questions', async () => {
    const ctx = freshLoad({ enabled: true, extendedPool: [
      makeExtRecord('gsm8k-easy', 4, { topic: 'Fractions', _difficulty: 'easy' }),
      makeExtRecord('gsm8k-hard', 4, { topic: 'Fractions', _difficulty: 'hard' }),
    ] });
    await settle();
    const pool = ctx.getPoolQuestions(4, ['Fractions'], 'hard');
    expect(pool.some(q => q._sourceId === 'gsm8k-hard')).toBe(true);
    expect(pool.some(q => q._sourceId === 'gsm8k-easy')).toBe(false);
  });
});

describe('real approved-pool data integrity guarantees', () => {
  // Loads the actual data/practice-pool-extended.json (not a fixture) to
  // concretely verify claims made in tools/word-problems/README.md, rather
  // than just asserting them in prose.
  const realPool = JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'data', 'practice-pool-extended.json'), 'utf8'));

  test('every approved record is grade 4-7 (the assessed, reviewed range)', () => {
    const grades = new Set(realPool.map(q => q.grade));
    for (const g of grades) expect(g).toBeGreaterThanOrEqual(4);
    for (const g of grades) expect(g).toBeLessThanOrEqual(7);
  });

  test('requesting an out-of-range grade never surfaces an extended-pool question', async () => {
    const ctx = freshLoad({ enabled: true, extendedPool: realPool });
    await settle();
    for (const grade of [1, 2, 3, 8, 9, 12]) {
      const pool = ctx.getPoolQuestions(grade, []);
      expect(pool.some(q => q._source === 'gsm8k')).toBe(false);
    }
  });

  test('extended-pool questions surface under their mapped practice topics', async () => {
    const ctx = freshLoad({ enabled: true, extendedPool: realPool });
    await settle();
    // Fractions-mapped GSM8K questions should appear when Fractions is selected
    const fractionsPool = ctx.getPoolQuestions(4, ['Fractions']);
    expect(fractionsPool.some(q => q._source === 'gsm8k')).toBe(true);
    // Geometry-mapped GSM8K questions should appear when Geometry is selected
    const geometryPool = ctx.getPoolQuestions(4, ['Geometry']);
    expect(geometryPool.some(q => q._source === 'gsm8k')).toBe(true);
    // A topic that maps to nothing (e.g. Place Value) should not surface GSM8K questions
    const otherPool = ctx.getPoolQuestions(4, ['Place Value']);
    expect(otherPool.some(q => q._source === 'gsm8k')).toBe(false);
  });

  test('topic mapping respects grade boundaries: grade 4 ratios question only appears under Word Problems', async () => {
    // Simulate a Grade 4 question whose source topic would map to Ratios & Proportions
    // for older grades, but Grade 4 has no such topic.
    const ctx = freshLoad({ enabled: true, extendedPool: [
      makeExtRecord('gsm8k-g4-ratio', 4, { _sourceTopic: 'Ratios & Rates' }),
    ] });
    await settle();
    expect(ctx.getPoolQuestions(4, ['Word Problems']).some(q => q._sourceId === 'gsm8k-g4-ratio')).toBe(true);
    expect(ctx.getPoolQuestions(4, ['Fractions']).some(q => q._sourceId === 'gsm8k-g4-ratio')).toBe(false);
    expect(ctx.getPoolQuestions(4, ['Geometry']).some(q => q._sourceId === 'gsm8k-g4-ratio')).toBe(false);
  });

  test('every approved record carries _difficulty and _sourceTopic metadata', () => {
    for (const q of realPool) {
      expect(q._difficulty).toMatch(/^(easy|medium|hard)$/);
      expect(typeof q._sourceTopic).toBe('string');
      expect(q._sourceTopic.length).toBeGreaterThan(0);
    }
  });

  test('only the finalized approved file is ever fetched — no candidate/rejected data path exists', () => {
    expect(SOURCE).not.toMatch(/candidates\.json|pilot_excluded|pilot_shortlist|assessed_records/);
    expect(SOURCE).toMatch(/practice-pool-extended\.json/);
  });
});

describe('points-eligible tally (session-based, source-agnostic)', () => {
  // Practice scoring is now verified server-side for any question source,
  // via a server-issued session (see api/practice-session-start.js,
  // api/practice-submit.js, migrations/002_practice_sessions.sql, and
  // "Practice scoring trust boundary" in tools/word-problems/README.md).
  // computePointsEligibleTally's only job now is: were these questions part
  // of a real session (hasSession=true) or local/offline fallback
  // (hasSession=false)? Question source (_source) no longer matters — an
  // earlier version of this function excluded gsm8k-sourced questions
  // specifically, as a stand-in until server-side verification existed for
  // everything; that carve-out is gone now that it does.
  test('with a session: every answered question counts, regardless of source', () => {
    const ctx = freshLoad({ enabled: true });
    const questions = [
      { _source: 'gsm8k', answer: '10', _userAnswer: '10' },
      { _source: 'gsm8k', answer: '10', _userAnswer: '99' },
      { _source: 'chatgpt', answer: '5', _userAnswer: '5' },
      { _source: 'algorithmic', answer: '7', _userAnswer: '9' },
    ];
    const tally = ctx.computePointsEligibleTally(questions, true);
    expect(tally.total).toBe(4);
    expect(tally.correct).toBe(2);
    expect(tally.excludedCount).toBe(0);
  });

  test('without a session (offline/fallback): nothing is points-eligible, regardless of source', () => {
    const ctx = freshLoad({ enabled: false });
    const questions = [
      { _source: 'chatgpt', answer: '5', _userAnswer: '5' },
      { _source: 'algorithmic', answer: '7', _userAnswer: '7' },
    ];
    const tally = ctx.computePointsEligibleTally(questions, false);
    expect(tally.excludedCount).toBe(2);
    expect(tally.total).toBe(0);
    expect(tally.correct).toBe(0);
  });

  test('an unanswered question in a real session is never counted as correct', () => {
    const ctx = freshLoad({ enabled: true });
    const questions = [{ _source: 'chatgpt', answer: '5' }]; // no _userAnswer set
    const tally = ctx.computePointsEligibleTally(questions, true);
    expect(tally.correct).toBe(0);
    expect(tally.total).toBe(1);
  });

  test('an all-GSM8K session is fully points-eligible now (no source-specific carve-out remains)', () => {
    const ctx = freshLoad({ enabled: true });
    const questions = [
      { _source: 'gsm8k', answer: '1', _userAnswer: '1' },
      { _source: 'gsm8k', answer: '2', _userAnswer: '2' },
    ];
    const tally = ctx.computePointsEligibleTally(questions, true);
    expect(tally.total).toBe(2);
    expect(tally.correct).toBe(2);
    expect(tally.excludedCount).toBe(0);
  });
});
