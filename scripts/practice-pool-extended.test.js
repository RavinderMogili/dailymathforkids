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

function freshLoad({ enabled = false, extendedPool = [], practicePool = [] } = {}) {
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
      location: { search: enabled ? '?enableExtendedPool=1' : '' },
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

  test('enabled via query param: extended pool contributes questions for its grade', async () => {
    const ctx = freshLoad({ enabled: true, extendedPool: [makeExtRecord('gsm8k-1', 4)] });
    expect(ctx.isExtendedPoolEnabled()).toBe(true);
    await settle();
    const pool = ctx.getPoolQuestions(4, []);
    expect(pool.some(q => q._sourceId === 'gsm8k-1')).toBe(true);
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
});
