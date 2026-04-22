/**
 * Find the latest available quiz page by checking today first, then going back up to 7 days.
 * Returns a path like '/daily/2026-04-18.html'.
 */
async function findLatestQuizPage(request) {
  for (let i = 0; i < 7; i++) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    const path = `/daily/${dateStr}.html`;
    try {
      const res = await request.get(path);
      if (res.ok()) return path;
    } catch { /* keep trying */ }
  }
  // Fallback to today even if 404 — test will fail with a clear error
  return '/daily/' + new Date().toISOString().slice(0, 10) + '.html';
}

module.exports = { findLatestQuizPage };
