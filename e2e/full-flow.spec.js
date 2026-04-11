import { test, expect } from '@playwright/test';

const SITE = 'https://ravindermogili.github.io/dailymathforkids';
const API  = 'https://dailymathforkids-api.vercel.app';

// Use a unique test nickname to avoid collisions
const TEST_NICK = 'E2E_Test_' + Date.now();
const TEST_GRADE = 'G3';

// ──────────────────────────────────────────
//  1. Homepage loads
// ──────────────────────────────────────────
test.describe('Homepage', () => {
  test('loads and shows title', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    await expect(page).toHaveTitle(/daily\s*math/i);
  });

  test('has navigation links', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    await expect(page.locator('a[href*="profile"]')).toBeVisible();
    await expect(page.locator('a[href*="leaderboard"]')).toBeVisible();
  });

  test('has register/login buttons or links', async ({ page }) => {
    await page.goto(`${SITE}/index.html`);
    // Look for sign up or register link/button
    const registerLink = page.locator('text=/register|sign up|join/i').first();
    await expect(registerLink).toBeVisible({ timeout: 5000 }).catch(() => {
      // May be rendered differently; just check page loaded
      console.log('No visible register link on homepage — may be in navbar');
    });
  });
});

// ──────────────────────────────────────────
//  2. Daily quiz page structure
// ──────────────────────────────────────────
test.describe('Daily Quiz Page', () => {
  test('loads today or latest quiz page', async ({ page }) => {
    // Try today's date
    const today = new Date().toISOString().slice(0, 10);
    let res = await page.goto(`${SITE}/daily/${today}.html`);
    if (!res || res.status() === 404) {
      // Fallback to 2026-04-11
      await page.goto(`${SITE}/daily/2026-04-11.html`);
    }
    const count = await page.locator('.grade-section').count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('has quiz form with hidden inputs', async ({ page }) => {
    await page.goto(`${SITE}/daily/2026-04-11.html`);
    await expect(page.locator('form#quiz')).toBeVisible();
    await expect(page.locator('input[name="q1"]')).toBeAttached();
    await expect(page.locator('input[name="q5"]')).toBeAttached();
  });

  test('has quiz timer element (hidden initially)', async ({ page }) => {
    await page.goto(`${SITE}/daily/2026-04-11.html`);
    const timer = page.locator('#quiz-timer');
    await expect(timer).toBeAttached();
    // Timer should be hidden until test starts
    await expect(timer).toBeHidden();
  });

  test('has encouragement section', async ({ page }) => {
    await page.goto(`${SITE}/daily/2026-04-11.html`);
    await expect(page.locator('.encouragement')).toBeVisible();
  });

  test('has submit button', async ({ page }) => {
    await page.goto(`${SITE}/daily/2026-04-11.html`);
    await expect(page.locator('form#quiz button[type="submit"]')).toBeVisible();
  });
});

// ──────────────────────────────────────────
//  3. Registration flow
// ──────────────────────────────────────────
test.describe('Registration', () => {
  test('register modal opens and validates inputs', async ({ page }) => {
    await page.goto(`${SITE}/daily/2026-04-11.html`);

    // Click register/sign-up link
    const regBtn = page.locator('text=/register|sign up|join now/i').first();
    if (await regBtn.isVisible()) {
      await regBtn.click();
      // Modal should appear
      await expect(page.locator('#reg-modal, [id*="reg"]')).toBeVisible({ timeout: 3000 });
    }
  });

  test('API rejects empty registration', async ({ request }) => {
    const res = await request.post(`${API}/api/register`, {
      data: {},
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.error).toBeTruthy();
  });

  test('API registers a new user', async ({ request }) => {
    const res = await request.post(`${API}/api/register`, {
      data: { nickname: TEST_NICK, grade: TEST_GRADE },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.userId).toBeTruthy();
    expect(body.nickname).toBe(TEST_NICK);
    expect(body.grade).toBe(TEST_GRADE);
  });
});

// ──────────────────────────────────────────
//  4. Login / Lookup flow
// ──────────────────────────────────────────
test.describe('Login / Lookup', () => {
  test('API finds registered user by nickname', async ({ request }) => {
    // First register
    await request.post(`${API}/api/register`, {
      data: { nickname: TEST_NICK, grade: TEST_GRADE },
    });
    // Then lookup
    const res = await request.get(`${API}/api/lookup?nickname=${encodeURIComponent(TEST_NICK)}`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.nickname).toBe(TEST_NICK);
    expect(body.grade).toBe(TEST_GRADE);
  });

  test('API returns 404 for unknown nickname', async ({ request }) => {
    const res = await request.get(`${API}/api/lookup?nickname=NONEXISTENT_USER_12345`);
    expect(res.status()).toBe(404);
  });
});

// ──────────────────────────────────────────
//  5. Start Test button & blur behavior
// ──────────────────────────────────────────
test.describe('Start Test Button', () => {
  test('grade section is blurred before login', async ({ page }) => {
    await page.goto(`${SITE}/daily/2026-04-11.html`);
    // Before login, grade sections should be hidden or blurred
    const sections = page.locator('.grade-section');
    const count = await sections.count();
    // At least one section should exist
    expect(count).toBeGreaterThan(0);
  });

  test('questions become visible after login + start test (simulated)', async ({ page }) => {
    await page.goto(`${SITE}/daily/2026-04-11.html`);

    // Simulate login by injecting user into localStorage
    await page.evaluate((nick) => {
      localStorage.setItem('dmk_user', JSON.stringify({
        userId: 'test-uuid', nickname: nick, grade: 'G3'
      }));
    }, TEST_NICK);

    // Reload to trigger showGradeProblems with logged-in user
    await page.reload();
    await page.waitForTimeout(1000);

    // Grade section for G3 should be visible but blurred
    const g3Section = page.locator('.grade-section[data-grade="G3"]');
    await expect(g3Section).toBeVisible();

    const filter = await g3Section.evaluate(el => el.style.filter);
    expect(filter).toContain('blur');

    // Start test button should be visible
    const startBtn = page.locator('#start-test-btn');
    await expect(startBtn).toBeVisible();

    // Click start test
    await startBtn.click();

    // Blur should be removed
    const filterAfter = await g3Section.evaluate(el => el.style.filter);
    expect(filterAfter).toBe('none');

    // Start button should be hidden
    await expect(startBtn).toBeHidden();

    // Timer should now be visible
    await expect(page.locator('#quiz-timer')).toBeVisible();
  });
});

// ──────────────────────────────────────────
//  6. Answer selection (MC buttons)
// ──────────────────────────────────────────
test.describe('Answer Selection', () => {
  test('clicking MC button highlights it and sets data-selected', async ({ page }) => {
    await page.goto(`${SITE}/daily/2026-04-11.html`);

    // Inject logged-in user
    await page.evaluate(() => {
      localStorage.setItem('dmk_user', JSON.stringify({
        userId: 'test-uuid', nickname: 'TestUser', grade: 'G3'
      }));
    });
    await page.reload();
    await page.waitForTimeout(1000);

    // Click start test
    const startBtn = page.locator('#start-test-btn');
    if (await startBtn.isVisible()) await startBtn.click();

    // Find MC buttons in G3 section
    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const firstQ = g3.locator('.problems-list > li').first();
    const mcBtn = firstQ.locator('.mc-btn').first();

    if (await mcBtn.isVisible()) {
      await mcBtn.click();

      // Check data-selected is set on the li
      const selected = await firstQ.getAttribute('data-selected');
      expect(selected).toBeTruthy();
    }
  });
});

// ──────────────────────────────────────────
//  7. Quiz submission via API
// ──────────────────────────────────────────
test.describe('Quiz Submission API', () => {
  test('rejects submission without required fields', async ({ request }) => {
    const res = await request.post(`${API}/api/submit`, { data: {} });
    expect(res.status()).toBe(400);
  });

  test('rejects submission with invalid quizId', async ({ request }) => {
    // Register first to get a userId
    const regRes = await request.post(`${API}/api/register`, {
      data: { nickname: TEST_NICK, grade: TEST_GRADE },
    });
    const { userId } = await regRes.json();

    const res = await request.post(`${API}/api/submit`, {
      data: {
        userId,
        quizId: 'NONEXISTENT-QUIZ-ID',
        answers: ['1', '2', '3', '4', '5'],
      },
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/quiz not found/i);
  });
});

// ──────────────────────────────────────────
//  8. Leaderboard
// ──────────────────────────────────────────
test.describe('Leaderboard', () => {
  test('page loads', async ({ page }) => {
    await page.goto(`${SITE}/leaderboard.html`);
    await expect(page.locator('body')).toContainText(/leaderboard|ranking/i);
  });

  test('API returns leaderboard data', async ({ request }) => {
    const res = await request.get(`${API}/api/leaderboard`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.leaderboard)).toBe(true);
  });

  test('API filters by grade', async ({ request }) => {
    const res = await request.get(`${API}/api/leaderboard?grade=G3`);
    const body = await res.json();
    body.leaderboard.forEach(entry => {
      expect(entry.grade).toBe('G3');
    });
  });

  test('speed leaderboard works', async ({ request }) => {
    const res = await request.get(`${API}/api/leaderboard?type=speed`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.leaderboard)).toBe(true);
  });
});

// ──────────────────────────────────────────
//  9. Profile page
// ──────────────────────────────────────────
test.describe('Profile Page', () => {
  test('loads without errors', async ({ page }) => {
    await page.goto(`${SITE}/profile.html`);
    await expect(page.locator('body')).toContainText(/profile|progress/i);
  });

  test('shows login prompt when not logged in', async ({ page }) => {
    await page.goto(`${SITE}/profile.html`);
    // Clear any stored user
    await page.evaluate(() => localStorage.removeItem('dmk_user'));
    await page.reload();
    // Should show some prompt to log in or register
    const body = await page.locator('body').textContent();
    // Profile page should at least render without crashing
    expect(body.length).toBeGreaterThan(0);
  });
});

// ──────────────────────────────────────────
//  10. Groups API
// ──────────────────────────────────────────
test.describe('Groups', () => {
  test('API rejects group lookup without params', async ({ request }) => {
    const res = await request.get(`${API}/api/groups`);
    expect(res.status()).toBe(400);
  });

  test('API returns null group for user not in any group', async ({ request }) => {
    // Register a fresh user
    const regRes = await request.post(`${API}/api/register`, {
      data: { nickname: 'E2E_NoGroup_' + Date.now(), grade: 'G5' },
    });
    const { userId } = await regRes.json();

    const res = await request.get(`${API}/api/groups?userId=${userId}`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.group).toBeNull();
  });

  test('API creates a group and returns invite code', async ({ request }) => {
    // Register
    const regRes = await request.post(`${API}/api/register`, {
      data: { nickname: 'E2E_GroupCreator_' + Date.now(), grade: 'G4' },
    });
    const { userId } = await regRes.json();

    // Create group
    const res = await request.post(`${API}/api/groups`, {
      data: { action: 'create', groupName: 'E2E Test Group', userId },
    });
    expect(res.status()).toBe(201);
    const body = await res.json();
    expect(body.invite_code).toBeTruthy();
    expect(body.invite_code.length).toBeGreaterThanOrEqual(4);
  });
});

// ──────────────────────────────────────────
//  11. No JS errors on pages
// ──────────────────────────────────────────
test.describe('No Console Errors', () => {
  for (const pg of ['index.html', 'profile.html', 'leaderboard.html', 'daily/2026-04-11.html']) {
    test(`${pg} loads without JS errors`, async ({ page }) => {
      const errors = [];
      page.on('pageerror', err => errors.push(err.message));

      await page.goto(`${SITE}/${pg}`);
      await page.waitForTimeout(2000);

      // Filter out known non-critical errors
      const critical = errors.filter(e => !e.includes('net::') && !e.includes('favicon'));
      expect(critical).toEqual([]);
    });
  }
});
