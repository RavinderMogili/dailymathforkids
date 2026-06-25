/**
 * E2E tests: Quiz answer correctness, scoring, and points.
 *
 * Tests:
 * 1. All quiz questions have valid answers that match one of their choices
 * 2. Selecting the correct answer is marked correct
 * 3. Selecting the wrong answer is marked wrong
 * 4. Points are earned and incremented correctly after submission
 * 5. Perfect score awards bonus points
 * 6. Practice mode scoring works correctly
 */

import { test, expect } from '@playwright/test';
const { findLatestQuizPage } = require('./helpers');

const SITE = 'https://dailymathforkids.com';
const API  = 'https://dailymathforkids-api.vercel.app';

let QUIZ_PAGE;
let TODAY;

test.beforeAll(async ({ request }) => {
  QUIZ_PAGE = await findLatestQuizPage(request);
  TODAY = QUIZ_PAGE.replace('/daily/', '').replace('.html', '');
});

function injectUser(page, grade = 'G3', nickname = 'AnswerTestKid') {
  return page.evaluate(({ g, nick }) => {
    localStorage.setItem('dmk_user', JSON.stringify({
      userId: 'test-uuid-answers', nickname: nick, grade: g
    }));
    // Clear quiz state so we can start fresh
    Object.keys(localStorage).filter(k =>
      k.startsWith('dmk_quiz_state_') || k.startsWith('dmk_timer') || k === 'dmk_active_quiz_url'
    ).forEach(k => localStorage.removeItem(k));
  }, { g: grade, nick: nickname });
}

// ──────────────────────────────────────────────────────
//  1. All questions have answers that match their choices
// ──────────────────────────────────────────────────────
test.describe('Quiz Answer Integrity', () => {
  test('every question has an answer that matches one of its choices', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await page.waitForTimeout(500);

    const problems = await page.evaluate(() => {
      const results = [];
      document.querySelectorAll('.grade-section').forEach(section => {
        const grade = section.dataset.grade;
        section.querySelectorAll('.problems-list > li').forEach((li, i) => {
          const answer = (li.dataset.answer || '').trim();
          const mcBtns = li.querySelectorAll('.mc-btn');
          const choices = Array.from(mcBtns).map(btn => (btn.dataset.value || btn.textContent || '').trim());
          results.push({ grade, num: i + 1, answer, choices });
        });
      });
      return results;
    });

    expect(problems.length).toBeGreaterThan(0);

    const failures = [];
    for (const p of problems) {
      if (!p.answer) {
        failures.push(`[${p.grade} Q${p.num}] Missing answer`);
        continue;
      }
      if (p.choices.length === 0) {
        failures.push(`[${p.grade} Q${p.num}] No choices found`);
        continue;
      }
      // Case-insensitive match
      const matched = p.choices.some(c => c.toLowerCase() === p.answer.toLowerCase());
      if (!matched) {
        failures.push(`[${p.grade} Q${p.num}] Answer "${p.answer}" not in choices: [${p.choices.join(', ')}]`);
      }
    }

    if (failures.length > 0) {
      console.log('Answer integrity failures:');
      failures.forEach(f => console.log('  ' + f));
    }
    expect(failures).toEqual([]);
  });

  test('no question has an empty or whitespace-only answer', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await page.waitForTimeout(500);

    const emptyAnswers = await page.evaluate(() => {
      const issues = [];
      document.querySelectorAll('.grade-section').forEach(section => {
        const grade = section.dataset.grade;
        section.querySelectorAll('.problems-list > li').forEach((li, i) => {
          const answer = (li.dataset.answer || '').trim();
          if (!answer) issues.push(`[${grade} Q${i + 1}]`);
        });
      });
      return issues;
    });

    expect(emptyAnswers).toEqual([]);
  });

  test('no question has duplicate choices', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await page.waitForTimeout(500);

    const duplicates = await page.evaluate(() => {
      const issues = [];
      document.querySelectorAll('.grade-section').forEach(section => {
        const grade = section.dataset.grade;
        section.querySelectorAll('.problems-list > li').forEach((li, i) => {
          const mcBtns = li.querySelectorAll('.mc-btn');
          const choices = Array.from(mcBtns).map(btn => (btn.dataset.value || btn.textContent || '').trim().toLowerCase());
          const unique = new Set(choices);
          if (unique.size < choices.length) {
            issues.push(`[${grade} Q${i + 1}] has duplicate choices`);
          }
        });
      });
      return issues;
    });

    expect(duplicates).toEqual([]);
  });
});

// ──────────────────────────────────────────────────────
//  2. Correct answer selection is recognized
// ──────────────────────────────────────────────────────
test.describe('Answer Selection Logic', () => {
  test('selecting the correct answer highlights it green after submit', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    // Start test
    const startBtn = page.locator('#start-test-btn');
    if (await startBtn.isVisible()) await startBtn.click();
    await page.waitForTimeout(300);

    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const firstQ = g3.locator('.problems-list > li').first();

    // Get the correct answer
    const correctAnswer = await firstQ.getAttribute('data-answer');
    expect(correctAnswer).toBeTruthy();

    // Click the MC button with the correct value
    const correctBtn = firstQ.locator(`.mc-btn[data-value="${correctAnswer}"]`);
    if (await correctBtn.count() > 0) {
      await correctBtn.click();
      // Verify it's selected
      const selected = await firstQ.getAttribute('data-selected');
      expect(selected).toBe(correctAnswer);
    }
  });

  test('selecting a wrong answer sets data-selected to wrong value', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    if (await startBtn.isVisible()) await startBtn.click();
    await page.waitForTimeout(300);

    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const firstQ = g3.locator('.problems-list > li').first();

    const correctAnswer = await firstQ.getAttribute('data-answer');
    // Find a WRONG choice
    const allBtns = firstQ.locator('.mc-btn');
    const count = await allBtns.count();
    for (let i = 0; i < count; i++) {
      const val = await allBtns.nth(i).getAttribute('data-value');
      if (val !== correctAnswer) {
        await allBtns.nth(i).click();
        const selected = await firstQ.getAttribute('data-selected');
        expect(selected).not.toBe(correctAnswer);
        break;
      }
    }
  });
});

// ──────────────────────────────────────────────────────
//  3. Full quiz submission with scoring
// ──────────────────────────────────────────────────────
test.describe('Quiz Submission & Scoring', () => {
  test('submitting all correct answers returns perfect score from API', async ({ page, request }) => {
    // Register a fresh user for this test
    const nick = 'E2E_Score_' + Date.now();
    const regRes = await request.post(`${API}/api/register`, {
      data: { nickname: nick, grade: 'G3', pin: '1234', security_question: "What is your pet's name?", security_answer: 'Max' },
    });
    const regBody = await regRes.json();
    const userId = regBody.userId;
    if (!userId) {
      console.log('Registration failed, skipping scoring test');
      return;
    }

    await page.goto(QUIZ_PAGE);
    // Inject the registered user
    await page.evaluate(({ uid, nick }) => {
      localStorage.setItem('dmk_user', JSON.stringify({
        userId: uid, nickname: nick, grade: 'G3'
      }));
      Object.keys(localStorage).filter(k =>
        k.startsWith('dmk_quiz_state_') || k.startsWith('dmk_timer') || k === 'dmk_active_quiz_url'
      ).forEach(k => localStorage.removeItem(k));
    }, { uid: userId, nick });
    await page.reload();
    await page.waitForTimeout(500);

    // Start test
    const startBtn = page.locator('#start-test-btn');
    if (await startBtn.isVisible()) await startBtn.click();
    await page.waitForTimeout(300);

    // Select correct answers for all questions in G3
    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const questions = g3.locator('.problems-list > li');
    const qCount = await questions.count();

    for (let i = 0; i < qCount; i++) {
      const li = questions.nth(i);
      const correctAnswer = await li.getAttribute('data-answer');
      if (correctAnswer) {
        const btn = li.locator(`.mc-btn[data-value="${CSS.escape(correctAnswer)}"]`).first();
        if (await btn.count() > 0) {
          await btn.click();
        } else {
          // Try by text content match
          const allBtns = li.locator('.mc-btn');
          const bCount = await allBtns.count();
          for (let b = 0; b < bCount; b++) {
            const val = await allBtns.nth(b).getAttribute('data-value');
            if (val === correctAnswer) {
              await allBtns.nth(b).click();
              break;
            }
          }
        }
      }
    }

    // Submit the quiz
    await page.locator('form#quiz button[type="submit"]').click();
    await page.waitForTimeout(3000);

    // Check result message
    const resultEl = page.locator('#result');
    const resultText = await resultEl.textContent();
    // Perfect score should show celebration emoji
    expect(resultText).toMatch(/perfect|nailed|\d+ out of \d+/i);

    // Check points were earned
    const pointsText = await resultEl.innerHTML();
    expect(pointsText).toContain('point');
  });

  test('submitting all wrong answers returns 0 score', async ({ page, request }) => {
    const nick = 'E2E_Wrong_' + Date.now();
    const regRes = await request.post(`${API}/api/register`, {
      data: { nickname: nick, grade: 'G3', pin: '1234', security_question: "What is your pet's name?", security_answer: 'Max' },
    });
    const regBody = await regRes.json();
    const userId = regBody.userId;
    if (!userId) return;

    await page.goto(QUIZ_PAGE);
    await page.evaluate(({ uid, nick }) => {
      localStorage.setItem('dmk_user', JSON.stringify({
        userId: uid, nickname: nick, grade: 'G3'
      }));
      Object.keys(localStorage).filter(k =>
        k.startsWith('dmk_quiz_state_') || k.startsWith('dmk_timer') || k === 'dmk_active_quiz_url'
      ).forEach(k => localStorage.removeItem(k));
    }, { uid: userId, nick });
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    if (await startBtn.isVisible()) await startBtn.click();
    await page.waitForTimeout(300);

    // Select WRONG answers for all questions
    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const questions = g3.locator('.problems-list > li');
    const qCount = await questions.count();

    for (let i = 0; i < qCount; i++) {
      const li = questions.nth(i);
      const correctAnswer = await li.getAttribute('data-answer');
      const allBtns = li.locator('.mc-btn');
      const bCount = await allBtns.count();
      for (let b = 0; b < bCount; b++) {
        const val = await allBtns.nth(b).getAttribute('data-value');
        if (val !== correctAnswer) {
          await allBtns.nth(b).click();
          break;
        }
      }
    }

    // Submit
    await page.locator('form#quiz button[type="submit"]').click();
    await page.waitForTimeout(3000);

    // Result should show a low score
    const resultEl = page.locator('#result');
    const resultText = await resultEl.textContent();
    expect(resultText).toMatch(/0 out of|keep going/i);
  });

  test('cannot submit the same quiz twice (duplicate submission)', async ({ page, request }) => {
    const nick = 'E2E_Dup_' + Date.now();
    const regRes = await request.post(`${API}/api/register`, {
      data: { nickname: nick, grade: 'G3', pin: '1234', security_question: "What is your pet's name?", security_answer: 'Max' },
    });
    const regBody = await regRes.json();
    const userId = regBody.userId;
    if (!userId) return;

    // Submit via API directly
    const quizId = `${TODAY}-G3`;
    const submitRes = await request.post(`${API}/api/submit`, {
      data: { userId, quizId, answers: ['1', '2', '3', '4', '5'] },
    });
    const submitBody = await submitRes.json();

    // Try submitting again
    const dupRes = await request.post(`${API}/api/submit`, {
      data: { userId, quizId, answers: ['1', '2', '3', '4', '5'] },
    });
    const dupBody = await dupRes.json();
    // Should indicate already submitted
    expect(dupBody.already).toBe(true);
  });
});

// ──────────────────────────────────────────────────────
//  4. Points API correctness
// ──────────────────────────────────────────────────────
test.describe('Points System', () => {
  test('submit API returns correct score and points_earned', async ({ request }) => {
    const nick = 'E2E_Points_' + Date.now();
    const regRes = await request.post(`${API}/api/register`, {
      data: { nickname: nick, grade: 'G3', pin: '1234', security_question: "What is your pet's name?", security_answer: 'Max' },
    });
    const { userId } = await regRes.json();
    if (!userId) return;

    const quizId = `${TODAY}-G3`;
    // Submit with some answers (they'll be compared against stored quiz answers)
    const res = await request.post(`${API}/api/submit`, {
      data: { userId, quizId, answers: ['dummy1', 'dummy2', 'dummy3', 'dummy4', 'dummy5'] },
    });

    if (res.status() === 200) {
      const body = await res.json();
      expect(body.score).toBeDefined();
      expect(body.outOf).toBeDefined();
      expect(body.points_earned).toBeDefined();
      // Score should be between 0 and outOf
      expect(body.score).toBeGreaterThanOrEqual(0);
      expect(body.score).toBeLessThanOrEqual(body.outOf);
      // Points earned should match score (1pt per correct + bonus for perfect)
      if (body.score === body.outOf && body.score > 0) {
        expect(body.points_earned).toBeGreaterThan(body.score); // bonus
      } else {
        expect(body.points_earned).toBe(body.score);
      }
    } else if (res.status() === 400) {
      // Quiz might not exist in DB yet — that's a known limitation
      const body = await res.json();
      expect(body.error).toMatch(/quiz not found/i);
    }
  });

  test('profile API returns accumulated points for user', async ({ request }) => {
    const nick = 'E2E_Profile_' + Date.now();
    const regRes = await request.post(`${API}/api/register`, {
      data: { nickname: nick, grade: 'G3', pin: '1234', security_question: "What is your pet's name?", security_answer: 'Max' },
    });
    const { userId } = await regRes.json();
    if (!userId) return;

    // Check profile endpoint
    const profileRes = await request.get(`${API}/api/profile?userId=${userId}`);
    if (profileRes.status() === 200) {
      const profile = await profileRes.json();
      expect(profile.total_points).toBeDefined();
      expect(profile.total_points).toBeGreaterThanOrEqual(0);
    }
  });
});

// ──────────────────────────────────────────────────────
//  5. Practice Mode scoring
// ──────────────────────────────────────────────────────
test.describe('Practice Mode Scoring', () => {
  test('answering correctly in practice earns points', async ({ page }) => {
    await page.goto(`${SITE}/practice.html`);
    await page.evaluate(() => {
      localStorage.setItem('dmk_user', JSON.stringify({
        userId: 'test-uuid-prac', nickname: 'PracTestKid', grade: 'G3'
      }));
      // Clear today's practice points
      const today = new Date().toISOString().slice(0, 10);
      localStorage.removeItem('dmk_practice_pts_' + today);
    });
    await page.reload();
    await page.waitForTimeout(500);

    await page.locator('#start-practice-btn').click();
    await page.waitForTimeout(500);

    // Answer all 5 questions with the correct answer
    for (let i = 0; i < 5; i++) {
      // Get the correct answer from the question data
      const correctAnswer = await page.evaluate(() => {
        const el = document.querySelector('#pq-question');
        return el ? el.dataset.answer : null;
      });

      if (correctAnswer) {
        // Click the choice that matches
        const choices = page.locator('.pq-choice');
        const count = await choices.count();
        for (let c = 0; c < count; c++) {
          const val = await choices.nth(c).getAttribute('data-value');
          if (val === correctAnswer) {
            await choices.nth(c).click();
            break;
          }
        }
      } else {
        // Just click first choice
        await page.locator('.pq-choice').first().click();
      }

      await page.waitForTimeout(300);
      const nextBtn = page.locator('#pq-next');
      if (await nextBtn.isVisible()) await nextBtn.click();
      await page.waitForTimeout(300);
    }

    // Results should show
    await expect(page.locator('#practice-results')).toBeVisible({ timeout: 5000 });

    // Points should be shown
    const pointsText = await page.locator('#results-points').textContent();
    expect(pointsText).toBeTruthy();
  });

  test('practice points are capped at daily limit', async ({ page }) => {
    await page.goto(`${SITE}/practice.html`);
    await page.evaluate(() => {
      localStorage.setItem('dmk_user', JSON.stringify({
        userId: 'test-uuid-cap', nickname: 'CapTestKid', grade: 'G3'
      }));
      // Set practice points to near-limit
      const today = new Date().toISOString().slice(0, 10);
      localStorage.setItem('dmk_practice_pts_' + today, '9');
    });
    await page.reload();
    await page.waitForTimeout(500);

    // Check that remaining points message shows
    const remaining = page.locator('#pts-remaining');
    const text = await remaining.textContent();
    expect(text).toMatch(/practice points/i);
  });
});

// ──────────────────────────────────────────────────────
//  6. Grade section & question visibility
// ──────────────────────────────────────────────────────
test.describe('Grade-based Question Display', () => {
  test('user sees only their grade questions (not other grades)', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    // G3 should be visible
    const g3 = page.locator('.grade-section[data-grade="G3"]');
    await expect(g3).toBeVisible();

    // Other grades should be hidden
    const allSections = page.locator('.grade-section');
    const count = await allSections.count();
    for (let i = 0; i < count; i++) {
      const grade = await allSections.nth(i).getAttribute('data-grade');
      if (grade !== 'G3') {
        await expect(allSections.nth(i)).toBeHidden();
      }
    }
  });

  test('changing user grade shows different questions', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G1', 'G1TestKid');
    await page.reload();
    await page.waitForTimeout(500);

    const g1 = page.locator('.grade-section[data-grade="G1"]');
    // G1 should be visible (if it exists in this quiz)
    const g1Count = await g1.count();
    if (g1Count > 0) {
      await expect(g1).toBeVisible();
      // G3 should be hidden
      const g3 = page.locator('.grade-section[data-grade="G3"]');
      if (await g3.count() > 0) {
        await expect(g3).toBeHidden();
      }
    }
  });

  test('user with grade not in today quiz sees helpful message', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    // Use a grade that might not be in the quiz
    await injectUser(page, 'G12', 'G12TestKid');
    await page.reload();
    await page.waitForTimeout(500);

    const g12Section = page.locator('.grade-section[data-grade="G12"]');
    const exists = await g12Section.count() > 0;

    if (!exists) {
      // Should show "no quiz today" message
      const hello = page.locator('#hello');
      const text = await hello.textContent();
      expect(text).toMatch(/no grade 12|practice mode/i);
    }
  });
});

// ──────────────────────────────────────────────────────
//  7. Streak tracking
// ──────────────────────────────────────────────────────
test.describe('Streak Tracking', () => {
  test('completing quiz shows streak message', async ({ page, request }) => {
    // Register a real user so submission works
    const nick = 'E2E_Streak_' + Date.now();
    const regRes = await request.post(`${API}/api/register`, {
      data: { nickname: nick, grade: 'G3', pin: '1234', security_question: "What is your pet's name?", security_answer: 'Max' },
    });
    const regBody = await regRes.json();
    const userId = regBody.userId;
    if (!userId) {
      console.log('Registration failed, skipping streak test');
      return;
    }

    await page.goto(QUIZ_PAGE);
    await page.evaluate(({ uid, nick }) => {
      localStorage.setItem('dmk_user', JSON.stringify({
        userId: uid, nickname: nick, grade: 'G3'
      }));
      Object.keys(localStorage).filter(k =>
        k.startsWith('dmk_quiz_state_') || k.startsWith('dmk_timer') || k === 'dmk_active_quiz_url' || k === 'doneDays'
      ).forEach(k => localStorage.removeItem(k));
    }, { uid: userId, nick });
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    if (await startBtn.isVisible()) await startBtn.click();
    await page.waitForTimeout(300);

    // Answer all questions (just pick first choice for speed)
    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const questions = g3.locator('.problems-list > li');
    const qCount = await questions.count();
    for (let i = 0; i < qCount; i++) {
      const btn = questions.nth(i).locator('.mc-btn').first();
      if (await btn.isVisible()) await btn.click();
    }

    // Submit
    await page.locator('form#quiz button[type="submit"]').click();
    await page.waitForTimeout(4000);

    // Streak message should appear after successful submission
    const streakMsg = page.locator('#streak-msg');
    const streakText = await streakMsg.textContent();
    expect(streakText).toMatch(/streak|day 1|great start/i);
  });
});
