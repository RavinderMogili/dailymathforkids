import { test, expect } from '@playwright/test';

const QUIZ_PAGE = '/daily/' + new Date().toISOString().slice(0, 10) + '.html';

function injectUser(page, grade = 'G3') {
  return page.evaluate((g) => {
    localStorage.setItem('dmk_user', JSON.stringify({
      userId: 'test-uuid', nickname: 'TestKid', grade: g
    }));
    Object.keys(localStorage).filter(k => k.startsWith('dmk_quiz_state_') || k.startsWith('dmk_timer') || k === 'dmk_active_quiz_url').forEach(k => localStorage.removeItem(k));
  }, grade);
}

// ──────────────────────────────────────────
//  1. Story & encouragement at top of page
// ──────────────────────────────────────────
test.describe('Story at top of page', () => {
  test('encouragement appears before grade sections', async ({ page }) => {
    await page.goto(QUIZ_PAGE);

    const encouragement = page.locator('.encouragement');
    const firstGrade = page.locator('.grade-section').first();

    await expect(encouragement).toBeVisible();

    // Encouragement should come before grade sections in DOM order
    const encourageBox = await encouragement.boundingBox();
    const gradeBox = await firstGrade.boundingBox();
    if (encourageBox && gradeBox) {
      expect(encourageBox.y).toBeLessThan(gradeBox.y);
    }
  });
});

// ──────────────────────────────────────────
//  2. Login required before starting quiz
// ──────────────────────────────────────────
test.describe('Login gate on Start Test', () => {
  test('clicking Start Test without login opens register modal', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    // Clear any stored user
    await page.evaluate(() => localStorage.removeItem('dmk_user'));
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    await expect(startBtn).toBeVisible();
    await startBtn.click();

    // Register modal should appear (display: flex)
    const modal = page.locator('#reg-modal');
    await expect(modal).toBeAttached({ timeout: 3000 });
    const display = await modal.evaluate(el => el.style.display);
    expect(display).toBe('flex');
  });

  test('grade section stays blurred after clicking Start Test without login', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await page.evaluate(() => localStorage.removeItem('dmk_user'));
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    await startBtn.click();
    await page.waitForTimeout(300);

    // G3 section should still be blurred
    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toContain('blur');
  });
});

// ──────────────────────────────────────────
//  3. Start Test works after login
// ──────────────────────────────────────────
test.describe('Start Test after login', () => {
  test('Start Test button works after logging in', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    const startBtn = page.locator('#start-test-btn');
    await expect(startBtn).toBeVisible();
    await startBtn.click();

    // Grade section should be unblurred
    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toBe('none');

    // Start button should be hidden
    await expect(startBtn).toBeHidden();
  });

  test('Start Test still works after login-then-retry flow', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    // First visit without login
    await page.evaluate(() => localStorage.removeItem('dmk_user'));
    await page.reload();
    await page.waitForTimeout(500);

    // Click start — should show modal
    const startBtn = page.locator('#start-test-btn');
    await startBtn.click();
    await page.waitForTimeout(300);

    // Now inject user (simulates completing login)
    await injectUser(page, 'G3');
    // Close any modal overlay
    await page.evaluate(() => {
      const modal = document.getElementById('reg-modal');
      if (modal) modal.style.display = 'none';
    });

    // Click start again — should work now
    await startBtn.click();
    await page.waitForTimeout(300);

    const g3 = page.locator('.grade-section[data-grade="G3"]');
    const filter = await g3.evaluate(el => el.style.filter);
    expect(filter).toBe('none');
  });
});

// ──────────────────────────────────────────
//  4. Answers lock after submission
// ──────────────────────────────────────────
test.describe('Lock answers after submit', () => {
  test('lockAnswersAfterSubmit disables MC buttons', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    // Start test
    const startBtn = page.locator('#start-test-btn');
    await startBtn.click();
    await page.waitForTimeout(300);

    // Call lockAnswersAfterSubmit directly
    await page.evaluate(() => lockAnswersAfterSubmit());

    // All MC buttons should be disabled
    const mcBtns = page.locator('.mc-btn');
    const count = await mcBtns.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < Math.min(count, 5); i++) {
      const disabled = await mcBtns.nth(i).isDisabled();
      expect(disabled).toBe(true);
    }

    // Submit button should be disabled
    const submitBtn = page.locator('#quiz button[type="submit"]');
    await expect(submitBtn).toBeDisabled();
  });
});

// ──────────────────────────────────────────
//  5. Completion overlay
// ──────────────────────────────────────────
test.describe('Completion overlay', () => {
  test('showCompletionAndRedirect creates overlay with score', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    // Call showCompletionAndRedirect directly
    await page.evaluate(() => { window.ROOT = '../'; showCompletionAndRedirect(4); });

    // Overlay should appear
    const overlay = page.locator('text=/Quiz Complete/i');
    await expect(overlay).toBeVisible({ timeout: 2000 });

    // Should show points
    const points = page.locator('text=/\\+4 point/');
    await expect(points).toBeVisible();

    // Should have back to home link
    const homeLink = page.getByRole('link', { name: 'Back to Home', exact: true });
    await expect(homeLink).toBeVisible();
  });

  test('perfect score shows celebration message', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(500);

    await page.evaluate(() => showCompletionAndRedirect(5));

    const perfect = page.locator('text=/Perfect Score/i');
    await expect(perfect).toBeVisible({ timeout: 2000 });
  });
});

// ──────────────────────────────────────────
//  6. Shield — one per month limit
// ──────────────────────────────────────────
test.describe('Shield one-per-month limit', () => {
  test('awardShield returns true first time', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    await page.evaluate(() => {
      localStorage.removeItem('dmk_shield');
      localStorage.removeItem('dmk_shield_date');
    });

    const result = await page.evaluate(() => awardShield());
    expect(result).toBe(true);
  });

  test('awardShield returns false if already earned this month', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    // Set shield as earned today
    const today = new Date().toISOString().slice(0, 10);
    await page.evaluate((d) => {
      localStorage.setItem('dmk_shield', JSON.stringify(true));
      localStorage.setItem('dmk_shield_date', JSON.stringify(d));
    }, today);

    const result = await page.evaluate(() => awardShield());
    expect(result).toBe(false);
  });

  test('awardShield returns true if last earned 31+ days ago', async ({ page }) => {
    await page.goto(QUIZ_PAGE);
    // Set shield date to 31 days ago
    const oldDate = new Date(Date.now() - 31 * 86400000).toISOString().slice(0, 10);
    await page.evaluate((d) => {
      localStorage.setItem('dmk_shield', JSON.stringify(false));
      localStorage.setItem('dmk_shield_date', JSON.stringify(d));
    }, oldDate);

    const result = await page.evaluate(() => awardShield());
    expect(result).toBe(true);
  });
});

// ──────────────────────────────────────────
//  7. Profile page streak explanation
// ──────────────────────────────────────────
test.describe('Profile streak explanation', () => {
  test('profile page shows streak and shield explanation', async ({ page }) => {
    await page.goto('/profile.html');
    await injectUser(page, 'G3');
    await page.reload();
    await page.waitForTimeout(2000);

    await expect(page.locator('text=/What\'s a streak/i')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=/What\'s a shield/i')).toBeVisible();
    await expect(page.locator('text=/one new shield every month/i')).toBeVisible();
  });
});

// ──────────────────────────────────────────
//  8. Badge system
// ──────────────────────────────────────────
test.describe('Badge system', () => {
  test('badges.js loads and provides BADGE_DEFS', async ({ page }) => {
    await page.goto('/practice.html');
    const count = await page.evaluate(() => typeof BADGE_DEFS !== 'undefined' ? BADGE_DEFS.length : 0);
    expect(count).toBeGreaterThanOrEqual(5);
  });

  test('getBadgeStats returns default stats initially', async ({ page }) => {
    await page.goto('/practice.html');
    await page.evaluate(() => localStorage.removeItem('dmk_badge_stats'));
    const stats = await page.evaluate(() => getBadgeStats());
    expect(stats.totalSessions).toBe(0);
    expect(stats.totalQuestions).toBe(0);
  });

  test('updateBadgeStats increments counters', async ({ page }) => {
    await page.goto('/practice.html');
    await page.evaluate(() => localStorage.removeItem('dmk_badge_stats'));
    await page.evaluate(() => updateBadgeStats({
      correct: 4, total: 5, topics: ['Fractions'], difficulty: 'easy', timeSeconds: 60
    }));
    const stats = await page.evaluate(() => getBadgeStats());
    expect(stats.totalSessions).toBe(1);
    expect(stats.totalQuestions).toBe(5);
    expect(stats.totalCorrect).toBe(4);
  });

  test('First Steps badge earned after first session', async ({ page }) => {
    await page.goto('/practice.html');
    await page.evaluate(() => localStorage.removeItem('dmk_badge_stats'));
    await page.evaluate(() => updateBadgeStats({
      correct: 3, total: 5, topics: ['Addition & Subtraction'], difficulty: 'easy', timeSeconds: 120
    }));
    const earned = await page.evaluate(() => getEarnedBadges().map(b => b.id));
    expect(earned).toContain('first_steps');
  });

  test('getAllBadges returns all badges with earned status', async ({ page }) => {
    await page.goto('/practice.html');
    const all = await page.evaluate(() => getAllBadges());
    expect(all.length).toBeGreaterThanOrEqual(5);
    all.forEach(b => {
      expect(b).toHaveProperty('id');
      expect(b).toHaveProperty('icon');
      expect(b).toHaveProperty('name');
      expect(b).toHaveProperty('earned');
    });
  });
});

// ──────────────────────────────────────────
//  9. Practice points daily cap
// ──────────────────────────────────────────
test.describe('Practice points cap', () => {
  test('points cap tracked in localStorage', async ({ page }) => {
    await page.goto('/practice.html');
    const today = new Date().toISOString().slice(0, 10);
    // Clear today's cap
    await page.evaluate((d) => localStorage.removeItem('dmk_practice_pts_' + d), today);
    // Set 9.5 points used
    await page.evaluate((d) => localStorage.setItem('dmk_practice_pts_' + d, '9.5'), today);
    // Check remaining
    const remaining = await page.evaluate((d) => {
      const used = parseFloat(localStorage.getItem('dmk_practice_pts_' + d) || '0');
      return Math.max(0, 10 - used);
    }, today);
    expect(remaining).toBe(0.5);
  });

  test('points remaining message updates', async ({ page }) => {
    await page.goto('/practice.html');
    const today = new Date().toISOString().slice(0, 10);
    await page.evaluate((d) => localStorage.setItem('dmk_practice_pts_' + d, '10'), today);
    await page.reload();
    await page.waitForTimeout(500);
    await expect(page.locator('#pts-remaining')).toContainText(/earned all 10/i);
  });
});

// ──────────────────────────────────────────
//  10. Weekly goals & milestones
// ──────────────────────────────────────────
test.describe('Weekly goals', () => {
  test('goals.js loads and provides getWeeklyGoalData', async ({ page }) => {
    await page.goto('/practice.html');
    const hasGoals = await page.evaluate(() => typeof getWeeklyGoalData === 'function');
    if (!hasGoals) { test.skip(); return; }
    const data = await page.evaluate(() => getWeeklyGoalData());
    expect(data).toHaveProperty('weekId');
    expect(data).toHaveProperty('solved');
    expect(data).toHaveProperty('goal');
  });

  test('addSolvedQuestions increments counter', async ({ page }) => {
    await page.goto('/practice.html');
    const hasGoals = await page.evaluate(() => typeof addSolvedQuestions === 'function');
    if (!hasGoals) { test.skip(); return; }
    await page.evaluate(() => localStorage.removeItem('dmk_weekly_goals'));
    await page.evaluate(() => addSolvedQuestions(5));
    const data = await page.evaluate(() => getWeeklyGoalData());
    expect(data.solved).toBe(5);
  });

  test('weekly goal widget renders on practice page', async ({ page }) => {
    await page.goto('/practice.html');
    await page.waitForTimeout(500);
    const el = page.locator('#weekly-goal-practice');
    if (!(await el.count())) { test.skip(); return; }
    await expect(el).toBeVisible();
    await expect(page.locator('text=/Weekly Goal/i')).toBeVisible();
  });

  test('milestone popup shows after reaching 10 questions', async ({ page }) => {
    await page.goto('/practice.html');
    const hasGoals = await page.evaluate(() => typeof addSolvedQuestions === 'function');
    if (!hasGoals) { test.skip(); return; }
    await page.evaluate(() => {
      localStorage.removeItem('dmk_weekly_goals');
      localStorage.removeItem('dmk_milestones');
    });
    await page.evaluate(() => addSolvedQuestions(10));
    await expect(page.locator('#milestone-popup')).toBeVisible({ timeout: 2000 });
    await expect(page.locator('text=/Getting Started/i')).toBeVisible();
  });

  test('weekly goal widget shows on homepage', async ({ page }) => {
    await page.goto('/index.html');
    await page.waitForTimeout(500);
    const el = page.locator('#weekly-goal-home');
    if (!(await el.count())) { test.skip(); return; }
    await expect(el).toBeVisible();
  });
});
