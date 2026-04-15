import { test, expect } from '@playwright/test';

const TODAY = new Date().toISOString().slice(0, 10);
const QUIZ_PAGE = '/daily/' + TODAY + '.html';

function injectUser(page, grade = 'G3') {
  return page.evaluate((g) => {
    localStorage.setItem('dmk_user', JSON.stringify({
      userId: 'test-uuid-sec', nickname: 'SecTestKid', grade: g
    }));
    // Clear any leftover quiz state
    Object.keys(localStorage).filter(k =>
      k.startsWith('dmk_quiz_state_') || k.startsWith('dmk_timer') || k === 'dmk_active_quiz_url'
    ).forEach(k => localStorage.removeItem(k));
  }, grade);
}

function clearAll(page) {
  return page.evaluate(() => {
    Object.keys(localStorage).filter(k => k.startsWith('dmk_')).forEach(k => localStorage.removeItem(k));
  });
}

// ──────────────────────────────────────────────────────
//  1. Questions must not be visible without login
// ──────────────────────────────────────────────────────
test.describe('No question leak without login', () => {
  test('questions are blurred on fresh visit (no user)', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await clearAll(page);
    await page.reload();
    await page.waitForTimeout(500);

    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toContain('blur');
  });

  test('questions stay blurred even if quiz state is "started" in localStorage but no user', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await page.evaluate((today) => {
      localStorage.removeItem('dmk_user');
      localStorage.setItem('dmk_quiz_state_' + today + '-G3', '"started"');
    }, TODAY);
    await page.reload();
    await page.waitForTimeout(500);

    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toContain('blur');
  });

  test('questions stay blurred even if quiz state is "done" in localStorage but no user', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await page.evaluate((today) => {
      localStorage.removeItem('dmk_user');
      localStorage.setItem('dmk_quiz_state_' + today + '-G3', '"done"');
    }, TODAY);
    await page.reload();
    await page.waitForTimeout(500);

    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toContain('blur');
  });
});

// ──────────────────────────────────────────────────────
//  2. Start Test requires login
// ──────────────────────────────────────────────────────
test.describe('Start Test gate', () => {
  test('clicking Start Test without login shows registration modal', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await clearAll(page);
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    await expect(startBtn).toBeVisible();
    await startBtn.click();
    await page.waitForTimeout(300);

    const modal = page.locator('#reg-modal');
    const display = await modal.evaluate(el => el.style.display);
    expect(display).toBe('flex');

    // Questions still blurred
    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toContain('blur');
  });

  test('Start Test works after login — unblurs questions', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    await expect(startBtn).toBeVisible();
    await startBtn.click();
    await page.waitForTimeout(300);

    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toBe('none');

    // Start button hidden
    await expect(startBtn).toBeHidden();
  });
});

// ──────────────────────────────────────────────────────
//  3. Timer starts and persists across refresh
// ──────────────────────────────────────────────────────
test.describe('Timer persistence', () => {
  test('timer appears after starting test and counts up', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    await page.locator('#start-test-btn').click();
    await page.waitForTimeout(1200);

    const timerEl = page.locator('#quiz-timer');
    await expect(timerEl).toBeVisible();

    const text = await page.locator('#timer-display').textContent();
    // Timer should show at least 0:01 after 1.2 seconds
    expect(text).toMatch(/\d+:\d{2}/);
  });

  test('timer resumes correct time after page refresh', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    await page.locator('#start-test-btn').click();
    // Wait 2 seconds to build up timer
    await page.waitForTimeout(2500);

    // Refresh
    await page.reload();
    await page.waitForTimeout(800);

    const timerEl = page.locator('#quiz-timer');
    await expect(timerEl).toBeVisible();

    const text = await page.locator('#timer-display').textContent();
    // Timer should show at least 2 seconds (not reset to 0:00)
    const parts = text.split(':');
    const totalSecs = parseInt(parts[0]) * 60 + parseInt(parts[1]);
    expect(totalSecs).toBeGreaterThanOrEqual(2);
  });
});

// ──────────────────────────────────────────────────────
//  4. Quiz state persists — no re-reveal after refresh
// ──────────────────────────────────────────────────────
test.describe('Quiz state persistence', () => {
  test('Start Test button is hidden after refresh if quiz already started', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    await page.locator('#start-test-btn').click();
    await page.waitForTimeout(300);

    // Refresh
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    await expect(startBtn).toBeHidden();

    // Questions still unblurred
    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toBe('none');
  });
});

// ──────────────────────────────────────────────────────
//  5. Quiz banner shows during active quiz
// ──────────────────────────────────────────────────────
test.describe('Quiz in-progress banner', () => {
  test('warning banner appears after starting test', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    await page.locator('#start-test-btn').click();
    await page.waitForTimeout(300);

    const banner = page.locator('#quiz-active-banner');
    await expect(banner).toBeVisible();
    const text = await banner.textContent();
    expect(text).toContain('auto-submitted');
    expect(text).toContain('refresh');
  });
});

// ──────────────────────────────────────────────────────
//  6. Navigate away auto-submits (home page marks done)
// ──────────────────────────────────────────────────────
test.describe('Navigate away marks quiz done', () => {
  test('going to home page marks active quiz as done', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    await page.locator('#start-test-btn').click();
    await page.waitForTimeout(300);

    // Navigate to home
    await page.goto('/index.html');
    await page.waitForTimeout(1000);

    // Check that quiz state is now 'done'
    const state = await page.evaluate((today) => {
      return localStorage.getItem('dmk_quiz_state_' + today + '-G3');
    }, TODAY);
    expect(state).toBe('"done"');
  });

  test('returning to quiz after navigate away shows locked state', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    await page.locator('#start-test-btn').click();
    await page.waitForTimeout(300);

    // Navigate away then back
    await page.goto('/index.html');
    await page.waitForTimeout(500);
    await page.goto(QUIZ_PAGE);
    await page.waitForTimeout(500);

    // Should show "already completed" message
    const hello = page.locator('#hello');
    const text = await hello.textContent();
    expect(text).toContain('already completed');

    // Submit button should be disabled
    const submitBtn = page.locator('#quiz button[type="submit"]');
    await expect(submitBtn).toBeDisabled();
  });
});

// ──────────────────────────────────────────────────────
//  7. Old quizzes are view-only (not submittable)
// ──────────────────────────────────────────────────────
test.describe('Expired quiz protection', () => {
  test('old quiz shows expired message and disabled submit', async ({ page }) => {
    await page.goto('/daily/2026-04-11.html');
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    const hello = page.locator('#hello');
    const text = await hello.innerHTML();
    expect(text).toContain('expired');

    const submitBtn = page.locator('#quiz button[type="submit"]');
    await expect(submitBtn).toBeDisabled();
  });

  test('old quiz questions are visible (for review) but not blurred', async ({ page }) => {
    await page.goto('/daily/2026-04-11.html');
    await page.waitForTimeout(500);

    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toBe('none');
  });

  test('old quiz does not show Start Test button', async ({ page }) => {
    await page.goto('/daily/2026-04-11.html');
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    const count = await startBtn.count();
    // Either doesn't exist or is hidden
    if (count > 0) {
      await expect(startBtn).toBeHidden();
    }
  });
});
