/**
 * Playwright global teardown: delete test accounts (E2E_* / test_<ts>_*)
 * created against the production API during test runs.
 *
 * Requires SUPABASE_SERVICE_ROLE in the environment — skipped otherwise:
 *   $env:SUPABASE_SERVICE_ROLE = "<service role key>"; npm test
 */

const API = 'https://dailymathforkids-api.vercel.app';

export default async function globalTeardown() {
  const key = (process.env.SUPABASE_SERVICE_ROLE || '').trim();
  if (!key) {
    console.log('[teardown] SUPABASE_SERVICE_ROLE not set — skipping test account cleanup.');
    return;
  }
  try {
    const res = await fetch(`${API}/api/cleanup-tests`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const body = await res.json();
    if (res.ok) {
      console.log(`[teardown] Deleted ${body.deleted} test account(s):`, body.nicknames);
    } else {
      console.warn('[teardown] Cleanup failed:', body.error);
    }
  } catch (e) {
    console.warn('[teardown] Cleanup request error:', e.message);
  }
}
