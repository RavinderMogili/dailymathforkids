import { test, expect } from '@playwright/test';
const { findLatestQuizPage } = require('./helpers');

const SITE = 'https://dailymathforkids.com';
const API  = 'https://dailymathforkids-api.vercel.app';

let QUIZ_PAGE;

test.beforeAll(async ({ request }) => {
  QUIZ_PAGE = await findLatestQuizPage(request);
});

function injectUser(page, grade = 'G3') {
  return page.evaluate((g) => {
    localStorage.setItem('dmk_user', JSON.stringify({
      userId: 'test-uuid-fb', nickname: 'FeedbackTestKid', grade: g
    }));
    Object.keys(localStorage).filter(k =>
      k.startsWith('dmk_quiz_state_') || k.startsWith('dmk_timer') || k === 'dmk_active_quiz_url'
    ).forEach(k => localStorage.removeItem(k));
  }, grade);
}

// ──────────────────────────────────────────
//  1. Feedback widget appears on all pages
// ──────────────────────────────────────────
test.describe('Feedback widget visibility', () => {
  const pages = ['index.html', 'practice.html', 'profile.html'];
  for (const pg of pages) {
    test(`feedback button visible on ${pg}`, async ({ page }) => {
      await page.goto(`${SITE}/${pg}`);
      await page.waitForTimeout(1000);
      await expect(page.locator('#dmk-feedback-btn')).toBeVisible();
    });
  }
});

// ──────────────────────────────────────────
//  2. Feedback panel opens and closes
// ──────────────────────────────────────────
test.describe('Feedback panel toggle', () => {
  test('clicking feedback button opens panel', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    await page.waitForTimeout(1000);

    await page.locator('#dmk-feedback-btn').click();
    await expect(page.locator('#dmk-feedback-panel')).toHaveClass(/open/);
    await expect(page.locator('#dmk-feedback-panel header h3')).toContainText('Share Your Feedback');
  });

  test('clicking close button closes panel', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    await page.waitForTimeout(1000);

    await page.locator('#dmk-feedback-btn').click();
    await expect(page.locator('#dmk-feedback-panel')).toHaveClass(/open/);

    await page.locator('#dmk-fb-close').click();
    await expect(page.locator('#dmk-feedback-panel')).not.toHaveClass(/open/);
  });

  test('clicking feedback button again closes panel', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    await page.waitForTimeout(1000);

    const btn = page.locator('#dmk-feedback-btn');
    await btn.click();
    await expect(page.locator('#dmk-feedback-panel')).toHaveClass(/open/);

    await btn.click();
    await expect(page.locator('#dmk-feedback-panel')).not.toHaveClass(/open/);
  });
});

// ──────────────────────────────────────────
//  3. Category selection
// ──────────────────────────────────────────
test.describe('Feedback categories', () => {
  test('default category is Suggestion', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    await page.waitForTimeout(1000);

    await page.locator('#dmk-feedback-btn').click();
    const active = page.locator('.fb-cat.active');
    await expect(active).toContainText('Suggestion');
  });

  test('clicking Bug selects it and deselects Suggestion', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    await page.waitForTimeout(1000);

    await page.locator('#dmk-feedback-btn').click();
    const bugCat = page.locator('.fb-cat[data-cat="bug"]');
    await bugCat.click();

    await expect(bugCat).toHaveClass(/active/);
    const suggestion = page.locator('.fb-cat[data-cat="suggestion"]');
    await expect(suggestion).not.toHaveClass(/active/);
  });

  test('all 4 categories exist', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    await page.waitForTimeout(1000);

    await page.locator('#dmk-feedback-btn').click();
    await expect(page.locator('.fb-cat')).toHaveCount(4);
    await expect(page.locator('.fb-cat[data-cat="suggestion"]')).toBeVisible();
    await expect(page.locator('.fb-cat[data-cat="bug"]')).toBeVisible();
    await expect(page.locator('.fb-cat[data-cat="question"]')).toBeVisible();
    await expect(page.locator('.fb-cat[data-cat="wrong_answer"]')).toBeVisible();
  });
});

// ──────────────────────────────────────────
//  4. Form validation
// ──────────────────────────────────────────
test.describe('Feedback form validation', () => {
  test('submit button does nothing when message is empty', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    await page.waitForTimeout(1000);

    await page.locator('#dmk-feedback-btn').click();
    // Don't type anything, just click submit
    await page.locator('#dmk-fb-submit').click();

    // Panel should still be open (not submitted)
    await expect(page.locator('#dmk-feedback-panel')).toHaveClass(/open/);
    // No success message
    await expect(page.locator('.fb-success')).toHaveCount(0);
  });
});

// ──────────────────────────────────────────
//  5. Feedback API endpoint
// ──────────────────────────────────────────
test.describe('Feedback API', () => {
  test('rejects empty message', async ({ request }) => {
    const res = await request.post(`${API}/api/feedback`, {
      data: { category: 'bug', message: '' },
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/message/i);
  });

  test('rejects invalid category', async ({ request }) => {
    const res = await request.post(`${API}/api/feedback`, {
      data: { category: 'hacking', message: 'test' },
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/category/i);
  });

  test('accepts valid feedback', async ({ request }) => {
    const res = await request.post(`${API}/api/feedback`, {
      data: {
        category: 'suggestion',
        message: 'E2E test feedback — please ignore',
        email: 'test@test.com',
        pageUrl: 'https://dailymathforkids.com/index.html',
      },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
  });

  test('accepts wrong_answer report with quiz details', async ({ request }) => {
    const res = await request.post(`${API}/api/feedback`, {
      data: {
        category: 'wrong_answer',
        message: 'Question #3: 2+2 — Answer should be 4 not 5',
        quizId: '2026-06-19-G4',
        questionNum: 3,
      },
    });
    expect(res.status()).toBe(200);
  });
});

// ──────────────────────────────────────────
//  6. Report question button on quiz page
// ──────────────────────────────────────────
test.describe('Report question button', () => {
  test('report button exists on quiz questions', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(1000);

    // Start the test to reveal questions
    const startBtn = page.locator('#start-test-btn');
    if (await startBtn.isVisible()) await startBtn.click();
    await page.waitForTimeout(500);

    // Check for report buttons
    const reportBtns = page.locator('.report-q-btn');
    const count = await reportBtns.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('report button has correct data-qnum attribute', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(1000);

    const startBtn = page.locator('#start-test-btn');
    if (await startBtn.isVisible()) await startBtn.click();
    await page.waitForTimeout(500);

    const firstReport = page.locator('.report-q-btn').first();
    if (await firstReport.count()) {
      const qnum = await firstReport.getAttribute('data-qnum');
      expect(parseInt(qnum)).toBeGreaterThanOrEqual(1);
    }
  });
});

// ──────────────────────────────────────────
//  7. No JS errors with feedback widget
// ──────────────────────────────────────────
test.describe('No JS errors from feedback widget', () => {
  for (const pg of ['index.html', 'practice.html', 'profile.html']) {
    test(`${pg} loads without JS errors from feedback widget`, async ({ page }) => {
      const errors = [];
      page.on('pageerror', err => errors.push(err.message));

      await page.goto(`${SITE}/${pg}`);
      await page.waitForTimeout(2000);

      // Open and close feedback panel
      const btn = page.locator('#dmk-feedback-btn');
      if (await btn.isVisible()) {
        await btn.click();
        await page.waitForTimeout(500);
        await btn.click();
      }

      const critical = errors.filter(e => !e.includes('net::') && !e.includes('favicon'));
      expect(critical).toEqual([]);
    });
  }
});
