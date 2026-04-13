// ── Weekly Goals & Milestones ─────────────────────────────────────────────
// Track questions solved this week, show progress toward weekly goal.

const GOALS_KEY = 'dmk_weekly_goals';
const MILESTONES_KEY = 'dmk_milestones';

function getWeekId() {
  const now = new Date();
  const jan1 = new Date(now.getFullYear(), 0, 1);
  const week = Math.ceil(((now - jan1) / 86400000 + jan1.getDay()) / 7);
  return now.getFullYear() + '-W' + String(week).padStart(2, '0');
}

function getWeeklyGoalData() {
  const weekId = getWeekId();
  const data = JSON.parse(localStorage.getItem(GOALS_KEY) || '{}');
  if (data.weekId !== weekId) {
    return { weekId, solved: 0, goal: 30, dailyDone: false };
  }
  return data;
}

function saveWeeklyGoalData(d) {
  localStorage.setItem(GOALS_KEY, JSON.stringify(d));
}

function addSolvedQuestions(count) {
  const d = getWeeklyGoalData();
  d.solved += count;
  saveWeeklyGoalData(d);
  checkMilestones(d.solved);
  return d;
}

function getWeeklyGoal() { return getWeeklyGoalData().goal || 30; }
function getWeeklySolved() { return getWeeklyGoalData().solved || 0; }

// ── Milestones ──────────────────────────────────────────────────────────
const MILESTONE_LEVELS = [
  { count: 10,   icon: '🌱', name: 'Getting Started',   msg: 'You solved 10 problems this week!' },
  { count: 30,   icon: '⭐', name: 'Weekly Goal!',       msg: 'Amazing! You hit your weekly goal of 30!' },
  { count: 50,   icon: '🔥', name: 'On Fire!',           msg: '50 problems this week — you\'re unstoppable!' },
  { count: 100,  icon: '💯', name: 'Century!',            msg: '100 problems in one week! Incredible!' },
  { count: 200,  icon: '🏆', name: 'Math Champion',      msg: '200 problems! You\'re a true math champion!' },
];

// Lifetime milestones
const LIFETIME_MILESTONES = [
  { count: 50,   icon: '🌟', name: '50 Questions',   msg: 'You\'ve solved 50 questions total!' },
  { count: 100,  icon: '💪', name: '100 Questions',  msg: '100 questions solved — you\'re growing!' },
  { count: 250,  icon: '🎯', name: '250 Questions',  msg: '250 questions! You\'re on a mission!' },
  { count: 500,  icon: '🏅', name: '500 Questions',  msg: 'Half a thousand! Legendary effort!' },
  { count: 1000, icon: '👑', name: '1000 Questions', msg: '1,000 questions solved! Math royalty!' },
];

function getMilestones() {
  return JSON.parse(localStorage.getItem(MILESTONES_KEY) || '{}');
}

function checkMilestones(weeklySolved) {
  const ms = getMilestones();
  const newOnes = [];

  // Weekly milestones
  const weekId = getWeekId();
  MILESTONE_LEVELS.forEach(m => {
    const key = weekId + '_' + m.count;
    if (weeklySolved >= m.count && !ms[key]) {
      ms[key] = { earned: new Date().toISOString(), ...m };
      newOnes.push(m);
    }
  });

  // Lifetime milestones
  const lifetime = getLifetimeTotal();
  LIFETIME_MILESTONES.forEach(m => {
    const key = 'lifetime_' + m.count;
    if (lifetime >= m.count && !ms[key]) {
      ms[key] = { earned: new Date().toISOString(), ...m };
      newOnes.push(m);
    }
  });

  localStorage.setItem(MILESTONES_KEY, JSON.stringify(ms));
  if (newOnes.length > 0) showMilestonePopup(newOnes[0]);
  return newOnes;
}

function getLifetimeTotal() {
  // Sum from badge stats if available
  try {
    const bs = JSON.parse(localStorage.getItem('dmk_badge_stats') || '{}');
    return (bs.totalQuestions || 0);
  } catch { return 0; }
}

function showMilestonePopup(m) {
  const existing = document.getElementById('milestone-popup');
  if (existing) existing.remove();
  const popup = document.createElement('div');
  popup.id = 'milestone-popup';
  popup.style.cssText = 'position:fixed;top:20px;right:20px;z-index:3000;background:linear-gradient(135deg,#fefce8,#fef3c7);border:2px solid #f59e0b;border-radius:16px;padding:16px 20px;box-shadow:0 8px 30px rgba(0,0,0,.15);animation:slideIn .4s ease;max-width:320px';
  popup.innerHTML = `
    <div style="font-size:2rem;text-align:center">${m.icon}</div>
    <p style="font-weight:700;text-align:center;margin:4px 0">${m.name}</p>
    <p style="font-size:.85rem;text-align:center;color:#92400e;margin:0">${m.msg}</p>
  `;
  document.body.appendChild(popup);
  setTimeout(() => popup.remove(), 4000);
}

// ── Render Widget ───────────────────────────────────────────────────────
function renderWeeklyGoalWidget(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const d = getWeeklyGoalData();
  const pct = Math.min(100, Math.round((d.solved / d.goal) * 100));
  const reached = d.solved >= d.goal;

  el.innerHTML = `
    <div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:2px solid #86efac;border-radius:14px;padding:14px 18px;margin:12px 0">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
        <span style="font-weight:700;font-size:.95rem">${reached ? '🎉' : '🎯'} Weekly Goal</span>
        <span style="font-size:.85rem;color:var(--muted)">${d.solved} / ${d.goal} problems</span>
      </div>
      <div style="background:#e2e8f0;border-radius:999px;height:14px;overflow:hidden">
        <div style="height:100%;border-radius:999px;background:${reached ? 'linear-gradient(90deg,#22c55e,#86efac)' : 'linear-gradient(90deg,#2563eb,#60a5fa)'};width:${pct}%;transition:width .6s ease;min-width:${d.solved > 0 ? '8px' : '0'}"></div>
      </div>
      <p style="margin:6px 0 0;font-size:.8rem;color:var(--muted);text-align:center">${
        reached ? '🏆 Goal reached! Keep going for bonus milestones!'
        : pct >= 50 ? `💪 Over halfway — ${d.goal - d.solved} more to go!`
        : `Solve ${d.goal - d.solved} more problems this week!`
      }</p>
    </div>
  `;
}
