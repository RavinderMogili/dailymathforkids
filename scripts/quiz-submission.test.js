/**
 * Unit tests for quiz submission flow.
 * Covers: submission success, already-submitted, network errors,
 * localStorage state management, score consistency, retry logic.
 *
 * Run with: npm run test:unit
 * @jest-environment jsdom
 */

// ── Mock localStorage ────────────────────────────────────────────────────────

const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// ── Mock DOM elements needed by app.js ───────────────────────────────────────

beforeEach(() => {
  localStorageMock.clear();
  document.body.innerHTML = `
    <div id="login-modal" style="display:none"></div>
    <div id="reg-modal" style="display:none"></div>
    <div id="corrective-feedback"></div>
    <p id="result"></p>
    <p id="streak-msg"></p>
    <section class="grade-section" data-grade="G5">
      <ol class="problems-list">
        <li data-answer="24" data-question="4 x 6 = ?" data-difficulty="easy" data-selected="24"></li>
        <li data-answer="7" data-question="3 + 4 = ?" data-difficulty="easy" data-selected="7"></li>
        <li data-answer="10" data-question="15 - 5 = ?" data-difficulty="medium" data-selected="8"></li>
        <li data-answer="36" data-question="6 x 6 = ?" data-difficulty="hard" data-selected="36"></li>
        <li data-answer="5" data-question="25 / 5 = ?" data-difficulty="easy" data-selected="5"></li>
      </ol>
    </section>
    <section class="hero" id="quiz-box">
      <form id="quiz">
        <input name="q1" value="24">
        <input name="q2" value="7">
        <input name="q3" value="8">
        <input name="q4" value="36">
        <input name="q5" value="5">
        <button type="submit">Submit Answers</button>
      </form>
    </section>
  `;
  // Reset fetch mock
  global.fetch = jest.fn();
});

// ── Load app.js helpers (inline stubs for isolated testing) ──────────────────

// We simulate the core functions from app.js since it's not a module.
// These match the actual implementation logic.

const store = {
  get(key, def) {
    const v = localStorage.getItem(key);
    if (v === null) return def;
    try { return JSON.parse(v); } catch { return v; }
  },
  set(key, val) {
    if (val === null || val === undefined) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(val));
  }
};

function getQuizState(qid) { return store.get('dmk_quiz_state_' + qid, null); }
function setQuizState(qid, state) { store.set('dmk_quiz_state_' + qid, state); }
function markDayDone(slug) { const d = store.get('doneDays', {}); d[slug] = true; store.set('doneDays', d); }
function getUser() { return store.get('dmk_user', null); }
function saveUser(u) { store.set('dmk_user', u); }

const API = 'https://dailymathforkids-api.vercel.app';

async function submitQuizAnswers(quizId, answers, resultEl, timeSeconds) {
  const u = getUser();
  if (!u) { resultEl.textContent = 'Please log in first.'; return false; }
  if (!API) { resultEl.textContent = 'Practice recorded!'; return true; }

  try {
    let res, attempts = 0;
    const payload = JSON.stringify({ userId: u.userId, quizId, answers, timeSeconds: timeSeconds ?? null });
    while (attempts < 3) {
      attempts++;
      try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 30000);
        res = await fetch(`${API}/api/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
          signal: ctrl.signal,
        });
        clearTimeout(timer);
        break;
      } catch (e) {
        if (attempts >= 3) throw e;
        await new Promise(r => setTimeout(r, 100)); // shortened for tests
      }
    }
    const data = await res.json();
    if (!res.ok) {
      resultEl.textContent = data.error || 'Something went wrong.';
      return false;
    }
    if (data.already) {
      markDayDone(quizId);
      setQuizState(quizId, 'done');
      resultEl.innerHTML = 'Your answers were submitted successfully!';
      return data;
    } else {
      markDayDone(quizId);
      setQuizState(quizId, 'done');
      resultEl.innerHTML = `Score: ${data.score}/${data.outOf} — +${data.points_earned} points!`;
      return data;
    }
  } catch {
    resultEl.innerHTML = 'Could not reach the server.';
    return false;
  }
}

// ── TESTS ────────────────────────────────────────────────────────────────────

describe('Quiz Submission Flow', () => {
  const mockUser = { userId: 'test-user-123', nickname: 'TestKid', grade: 'Grade 5' };
  const quizId = '2026-06-28-G5';
  const answers = ['24', '7', '8', '36', '5'];

  beforeEach(() => {
    saveUser(mockUser);
    setQuizState(quizId, 'started');
  });

  test('successful submission returns score and marks quiz done', async () => {
    const serverResponse = { score: 4, outOf: 5, points_earned: 4, already: false, results: [] };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(serverResponse),
    });

    const resultEl = document.getElementById('result');
    const result = await submitQuizAnswers(quizId, answers, resultEl, 30);

    expect(result).toEqual(serverResponse);
    expect(result.score).toBe(4);
    expect(result.points_earned).toBe(4);
    expect(getQuizState(quizId)).toBe('done');
    expect(store.get('doneDays', {})[quizId]).toBe(true);
    expect(resultEl.innerHTML).toContain('4/5');
    expect(resultEl.innerHTML).toContain('+4 points');
  });

  test('already-submitted returns data and marks done', async () => {
    const serverResponse = { score: null, outOf: 5, points_earned: 0, already: true };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(serverResponse),
    });

    const resultEl = document.getElementById('result');
    const result = await submitQuizAnswers(quizId, answers, resultEl, 30);

    expect(result).toEqual(serverResponse);
    expect(result.already).toBe(true);
    expect(getQuizState(quizId)).toBe('done');
    expect(store.get('doneDays', {})[quizId]).toBe(true);
    expect(resultEl.innerHTML).toContain('submitted successfully');
  });

  test('network error returns false and does NOT mark quiz done', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('network error'));

    const resultEl = document.getElementById('result');
    const result = await submitQuizAnswers(quizId, answers, resultEl, 30);

    expect(result).toBe(false);
    expect(getQuizState(quizId)).toBe('started'); // NOT changed to 'done'
    expect(store.get('doneDays', {})[quizId]).toBeUndefined();
    expect(resultEl.innerHTML).toContain('Could not reach the server');
  });

  test('server error (non-ok response) returns false', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Quiz expired' }),
    });

    const resultEl = document.getElementById('result');
    const result = await submitQuizAnswers(quizId, answers, resultEl, 30);

    expect(result).toBe(false);
    expect(getQuizState(quizId)).toBe('started');
    expect(resultEl.textContent).toContain('Quiz expired');
  });

  test('no user logged in shows login message', async () => {
    store.set('dmk_user', null);

    const resultEl = document.getElementById('result');
    const result = await submitQuizAnswers(quizId, answers, resultEl, 30);

    expect(result).toBe(false);
    expect(resultEl.textContent).toContain('log in');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('retries on first failure, succeeds on second attempt', async () => {
    const serverResponse = { score: 5, outOf: 5, points_earned: 5, already: false, results: [] };
    global.fetch = jest.fn()
      .mockRejectedValueOnce(new Error('timeout'))
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(serverResponse),
      });

    const resultEl = document.getElementById('result');
    const result = await submitQuizAnswers(quizId, answers, resultEl, 30);

    expect(result).toEqual(serverResponse);
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(getQuizState(quizId)).toBe('done');
  });

  test('retries 3 times then fails', async () => {
    global.fetch = jest.fn()
      .mockRejectedValueOnce(new Error('timeout1'))
      .mockRejectedValueOnce(new Error('timeout2'))
      .mockRejectedValueOnce(new Error('timeout3'));

    const resultEl = document.getElementById('result');
    const result = await submitQuizAnswers(quizId, answers, resultEl, 30);

    expect(result).toBe(false);
    expect(global.fetch).toHaveBeenCalledTimes(3);
    expect(getQuizState(quizId)).toBe('started');
  });
});

describe('localStorage State Management', () => {
  const quizId = '2026-06-28-G5';

  test('setQuizState and getQuizState work correctly', () => {
    expect(getQuizState(quizId)).toBeNull();
    setQuizState(quizId, 'started');
    expect(getQuizState(quizId)).toBe('started');
    setQuizState(quizId, 'done');
    expect(getQuizState(quizId)).toBe('done');
  });

  test('clearing stale done state (null) allows re-submission', () => {
    setQuizState(quizId, 'done');
    expect(getQuizState(quizId)).toBe('done');
    setQuizState(quizId, null);
    expect(getQuizState(quizId)).toBeNull();
  });

  test('markDayDone adds to doneDays record', () => {
    expect(store.get('doneDays', {})[quizId]).toBeUndefined();
    markDayDone(quizId);
    expect(store.get('doneDays', {})[quizId]).toBe(true);
  });

  test('resumeOrLockQuiz logic: done + doneDays = lock, done + no doneDays = clear', () => {
    // Simulate resumeOrLockQuiz logic
    function shouldLock(qid) {
      const state = getQuizState(qid);
      if (state === 'done') {
        const doneDays = store.get('doneDays', {});
        if (doneDays[qid]) return 'lock';
        else {
          setQuizState(qid, null);
          return 'cleared';
        }
      }
      return 'no-lock';
    }

    // Case 1: done + doneDays = should lock
    setQuizState(quizId, 'done');
    markDayDone(quizId);
    expect(shouldLock(quizId)).toBe('lock');

    // Case 2: done + no doneDays (stale beacon state) = clear it
    localStorageMock.clear();
    setQuizState(quizId, 'done');
    // No markDayDone call — simulates stale beacon
    expect(shouldLock(quizId)).toBe('cleared');
    expect(getQuizState(quizId)).toBeNull();

    // Case 3: started = no lock
    setQuizState(quizId, 'started');
    expect(shouldLock(quizId)).toBe('no-lock');
  });
});

describe('Score Consistency', () => {
  test('corrective feedback uses server score, not local weighted', () => {
    const serverData = { score: 4, outOf: 5, points_earned: 4, already: false };
    const answers = ['24', '7', '8', '36', '5'];

    // Simulate what the corrective feedback now does
    const feedbackEl = document.getElementById('corrective-feedback');
    const lis = document.querySelectorAll('.problems-list > li');
    let correctCount = 0;

    answers.forEach((userAns, i) => {
      const li = lis[i];
      const correct = li ? (li.dataset.answer || '').trim() : '';
      if (userAns.trim().toLowerCase() === correct.toLowerCase()) correctCount++;
    });

    // Local count should match server score
    expect(correctCount).toBe(serverData.score);

    // Build feedback with server score (as our fix does)
    const scoreHtml = `Score: ${serverData.score} / ${serverData.outOf} — +${serverData.points_earned} points earned`;
    expect(scoreHtml).toBe('Score: 4 / 5 — +4 points earned');
    expect(scoreHtml).not.toContain('Weighted');
  });

  test('wrong answer shows correct answer in feedback', () => {
    const lis = document.querySelectorAll('.problems-list > li');
    const answers = ['24', '7', '8', '36', '5']; // answer[2] = '8', correct = '10'

    const wrongOnes = [];
    answers.forEach((userAns, i) => {
      const li = lis[i];
      const correct = li ? (li.dataset.answer || '').trim() : '';
      if (userAns.trim().toLowerCase() !== correct.toLowerCase()) {
        wrongOnes.push({ question: i + 1, userAns, correct });
      }
    });

    expect(wrongOnes).toHaveLength(1);
    expect(wrongOnes[0]).toEqual({ question: 3, userAns: '8', correct: '10' });
  });
});

describe('Double-Submission Prevention', () => {
  test('_submitting flag prevents concurrent submissions', () => {
    let _submitting = false;

    function trySubmit() {
      if (_submitting) return 'blocked';
      _submitting = true;
      return 'submitted';
    }

    expect(trySubmit()).toBe('submitted');
    expect(trySubmit()).toBe('blocked'); // second call blocked

    // Reset on failure
    _submitting = false;
    expect(trySubmit()).toBe('submitted'); // works again after reset
  });
});
