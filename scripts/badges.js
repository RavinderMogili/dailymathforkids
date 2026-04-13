// ── Badge System ─────────────────────────────────────────────────────────
// Badges are earned through practice and daily quizzes.
// Tracked in localStorage, synced to profile display.

const BADGE_DEFS = [
  {
    id: 'fraction_master',
    icon: '🏅',
    name: 'Fraction Master',
    desc: 'Complete 50 fraction problems',
    check: (s) => s.topicCounts['Fractions'] >= 50,
  },
  {
    id: 'speed_demon',
    icon: '⚡',
    name: 'Speed Demon',
    desc: 'Solve 10 problems in under 2 minutes',
    check: (s) => s.speedSessions > 0,
  },
  {
    id: 'sharpshooter',
    icon: '🎯',
    name: 'Sharpshooter',
    desc: 'Get 20 correct in a row',
    check: (s) => s.bestStreak >= 20,
  },
  {
    id: 'explorer',
    icon: '📚',
    name: 'Explorer',
    desc: 'Try problems from 5 different topics',
    check: (s) => s.uniqueTopics >= 5,
  },
  {
    id: 'practice_pro',
    icon: '🔥',
    name: 'Practice Pro',
    desc: 'Practice 7 days in a row',
    check: (s) => s.practiceStreak >= 7,
  },
  {
    id: 'first_steps',
    icon: '🌱',
    name: 'First Steps',
    desc: 'Complete your first practice session',
    check: (s) => s.totalSessions >= 1,
  },
  {
    id: 'century',
    icon: '💯',
    name: 'Century Club',
    desc: 'Answer 100 practice questions',
    check: (s) => s.totalQuestions >= 100,
  },
  {
    id: 'perfectionist',
    icon: '✨',
    name: 'Perfectionist',
    desc: 'Get 100% on a 20-question practice',
    check: (s) => s.perfectTwenty > 0,
  },
  {
    id: 'math_machine',
    icon: '🤖',
    name: 'Math Machine',
    desc: 'Answer 500 practice questions',
    check: (s) => s.totalQuestions >= 500,
  },
  {
    id: 'daily_duo',
    icon: '🤝',
    name: 'Daily + Practice',
    desc: 'Do both a daily quiz and practice in one day',
    check: (s) => s.dailyAndPractice > 0,
  },
];

// ── Badge Stats Storage ─────────────────────────────────────────────────
const BADGE_STATS_KEY = 'dmk_badge_stats';

function getBadgeStats() {
  try {
    return JSON.parse(localStorage.getItem(BADGE_STATS_KEY)) || defaultBadgeStats();
  } catch { return defaultBadgeStats(); }
}

function saveBadgeStats(s) {
  localStorage.setItem(BADGE_STATS_KEY, JSON.stringify(s));
}

function defaultBadgeStats() {
  return {
    topicCounts: {},
    speedSessions: 0,
    bestStreak: 0,
    currentStreak: 0,
    uniqueTopics: 0,
    practiceStreak: 0,
    practiceDays: [],
    totalSessions: 0,
    totalQuestions: 0,
    totalCorrect: 0,
    perfectTwenty: 0,
    dailyAndPractice: 0,
  };
}

// Call after each practice session
function updateBadgeStats(sessionData) {
  const s = getBadgeStats();

  // Total sessions and questions
  s.totalSessions = (s.totalSessions || 0) + 1;
  s.totalQuestions = (s.totalQuestions || 0) + sessionData.total;
  s.totalCorrect = (s.totalCorrect || 0) + sessionData.correct;

  // Topic counts
  if (!s.topicCounts) s.topicCounts = {};
  (sessionData.topics || []).forEach(t => {
    s.topicCounts[t] = (s.topicCounts[t] || 0) + Math.ceil(sessionData.total / sessionData.topics.length);
  });

  // Unique topics
  s.uniqueTopics = Object.keys(s.topicCounts).length;

  // Speed demon: 10+ problems in under 2 minutes
  if (sessionData.total >= 10 && sessionData.timeSeconds <= 120 && sessionData.correct >= Math.floor(sessionData.total * 0.8)) {
    s.speedSessions = (s.speedSessions || 0) + 1;
  }

  // Correct streak
  s.currentStreak = (s.currentStreak || 0) + sessionData.correct;
  if (sessionData.correct < sessionData.total) {
    // Streak broken at first wrong answer
    s.currentStreak = sessionData.total - sessionData.correct > 0 ? 0 : s.currentStreak;
  }
  s.bestStreak = Math.max(s.bestStreak || 0, s.currentStreak);

  // Perfect 20
  if (sessionData.total >= 20 && sessionData.correct === sessionData.total) {
    s.perfectTwenty = (s.perfectTwenty || 0) + 1;
  }

  // Practice streak (days in a row)
  const today = new Date().toISOString().slice(0, 10);
  if (!s.practiceDays) s.practiceDays = [];
  if (!s.practiceDays.includes(today)) {
    s.practiceDays.push(today);
    s.practiceDays.sort();
  }
  s.practiceStreak = calcPracticeStreak(s.practiceDays);

  // Daily + Practice combo
  const dailySubs = JSON.parse(localStorage.getItem('dmk_user') || '{}');
  // Simple check: if they did a daily quiz today, mark combo
  if (localStorage.getItem('dmk_daily_done_' + today)) {
    s.dailyAndPractice = (s.dailyAndPractice || 0) + 1;
  }

  saveBadgeStats(s);
  return s;
}

function calcPracticeStreak(days) {
  if (!days || days.length === 0) return 0;
  const sorted = [...days].sort().reverse();
  let streak = 1;
  for (let i = 0; i < sorted.length - 1; i++) {
    const curr = new Date(sorted[i]);
    const prev = new Date(sorted[i + 1]);
    const diff = (curr - prev) / (1000 * 60 * 60 * 24);
    if (diff === 1) streak++;
    else break;
  }
  return streak;
}

// Get earned badges
function getEarnedBadges() {
  const s = getBadgeStats();
  return BADGE_DEFS.filter(b => {
    try { return b.check(s); } catch { return false; }
  });
}

// Get all badges with earned status
function getAllBadges() {
  const s = getBadgeStats();
  return BADGE_DEFS.map(b => {
    let earned = false;
    try { earned = b.check(s); } catch {}
    return { ...b, earned };
  });
}
