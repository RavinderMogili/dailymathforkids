// Daily Math for Kids — shared app logic
// Pages set window.DMK_API and window.DMK_ROOT before loading this script.

const API = (window.DMK_API || '').replace(/\/$/, '');
const ROOT = window.DMK_ROOT || './';

// ── LocalStorage helpers ─────────────────────────────────────────────────────

const store = {
  get(k, def = null) {
    try { const v = localStorage.getItem(k); return v === null ? def : JSON.parse(v); } catch { return def; }
  },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};

// ── User ─────────────────────────────────────────────────────────────────────

function getUser() { return store.get('dmk_user', null); }
function saveUser(u) { store.set('dmk_user', u); }

function renderBadge() {
  const u = getUser();
  document.querySelectorAll('.user-badge').forEach(el => {
    if (u) {
      el.innerHTML =
        `<span class="badge-name">⭐ ${escHtml(u.nickname)}</span>` +
        `<a class="badge-link" href="${ROOT}profile.html">📊 My Progress</a>` +
        `<a class="badge-link" href="${ROOT}practice.html">🎯 Practice</a>` +
        `<button class="badge-link" onclick="showGroupModal()">🤝 Group</button>` +
        `<button class="badge-link" onclick="logOut()">Log out</button>`;
    } else {
      el.innerHTML =
        `<button class="badge-btn" onclick="showRegModal()">Join Free 🚀</button>` +
        `<button class="badge-link" onclick="showLoginModal()">Log in</button>`;
    }
  });
  const joinCta = document.getElementById('join-cta');
  if (joinCta) joinCta.style.display = u ? 'none' : '';
}

function logOut() {
  const activeQuiz = _getActiveQuizId();
  if (activeQuiz && getQuizState(activeQuiz) === 'started') {
    const ok = confirm('You have an active quiz in progress! If you log out, your answers will be auto-submitted. Continue?');
    if (!ok) return;
    _autoSubmitQuiz();
  }
  store.set('dmk_user', null);
  store.set('dmk_group', null);
  renderBadge();
}

function _getActiveQuizId() {
  if (typeof QUIZ_DATE === 'undefined') return null;
  const code = window.DMK_ACTIVE_GRADE || 'G3';
  return QUIZ_DATE + '-' + code;
}

function _autoSubmitQuiz() {
  const form = document.getElementById('quiz');
  if (form) {
    form.dispatchEvent(new Event('submit', { cancelable: true }));
  }
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Modal injection ──────────────────────────────────────────────────────────

function injectModals() {
  if (document.getElementById('dmk-modals')) return;
  const grades = ['Grade 1','Grade 2','Grade 3','Grade 4','Grade 5','Grade 6','Grade 7','Grade 8','Grade 9','Grade 10','Grade 11','Grade 12'];
  const opts = grades.map(g => `<option value="${g}">${g}</option>`).join('');

  document.body.insertAdjacentHTML('beforeend', `
<div id="dmk-modals">
  <!-- Registration modal -->
  <div id="reg-modal" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="reg-title" style="display:none">
    <div class="modal-card">
      <button class="modal-close" onclick="hideRegModal()" aria-label="Close">✕</button>
      <h2 class="modal-title" id="reg-title">Join Daily Math for Kids! 🧮</h2>
      <p class="modal-sub">Free daily practice — track your personal best and grow every day! 🌱</p>
      <form id="reg-form" onsubmit="submitReg(event)" novalidate>
        <label class="form-label">Nickname <span class="req">*</span>
          <input id="reg-nickname" class="form-input" placeholder="e.g. MathStar99" required maxlength="30" autocomplete="off"/>
        </label>
        <label class="form-label">Grade <span class="req">*</span>
          <select id="reg-grade" class="form-input" required>
            <option value="">Choose your grade…</option>${opts}
          </select>
        </label>
        <label class="form-label">School name <small class="opt-label">(optional)</small>
          <input id="reg-school" class="form-input" placeholder="e.g. Hillcrest Elementary" maxlength="60"/>
        </label>
        <label class="form-label">City <small class="opt-label">(optional)</small>
          <input id="reg-city" class="form-input" placeholder="e.g. Moncton" maxlength="40"/>
        </label>
        <label class="form-label">Parent / Guardian email <small class="opt-label">(optional)</small>
          <input id="reg-parent-email" class="form-input" type="email" placeholder="parent@example.com" maxlength="100"/>
          <small class="opt-label" style="margin-top:2px">📧 We’ll send a weekly progress report. Never shared or used for marketing.</small>
        </label>
        <p id="reg-msg" class="form-msg" aria-live="polite"></p>
        <p class="privacy-note">🔒 Only your nickname and grade are stored. Your progress is private.</p>
        <button type="submit" class="btn-primary">Join for Free! 🎉</button>
      </form>
      <p class="modal-note">Already joined? <button class="link-btn" onclick="showLoginModal()">Log in with nickname</button></p>
    </div>
  </div>

  <!-- Group modal -->
  <div id="group-modal" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="group-title" style="display:none">
    <div class="modal-card">
      <button class="modal-close" onclick="hideGroupModal()" aria-label="Close">✕</button>
      <h2 class="modal-title" id="group-title">🤝 Family / Class Goal</h2>
      <p class="modal-sub">Practice together and celebrate as a team — no public ranking!</p>
      <div style="display:flex;flex-direction:column;gap:14px">
        <div>
          <strong>Create a new group</strong>
          <label class="form-label" style="margin-top:8px">Group name
            <input id="group-name-input" class="form-input" placeholder="e.g. Smith Family" maxlength="50"/>
          </label>
          <button class="btn-primary" onclick="createGroup()" style="margin-top:4px">Create &amp; Get Code</button>
        </div>
        <hr style="border:none;border-top:1px solid #eee"/>
        <div>
          <strong>Join an existing group</strong>
          <label class="form-label" style="margin-top:8px">Invite code
            <input id="group-code-input" class="form-input" placeholder="e.g. ABC123" maxlength="10" style="text-transform:uppercase"/>
          </label>
          <button class="btn-secondary" onclick="joinGroup()" style="margin-top:4px">Join Group</button>
        </div>
      </div>
      <p id="group-msg" class="form-msg" aria-live="polite" style="margin-top:12px"></p>
    </div>
  </div>

  <!-- Login modal -->
  <div id="login-modal" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="login-title" style="display:none">
    <div class="modal-card">
      <button class="modal-close" onclick="hideLoginModal()" aria-label="Close">✕</button>
      <h2 class="modal-title" id="login-title">Welcome Back! 👋</h2>
      <p class="modal-sub">Enter your nickname to continue tracking your progress.</p>
      <form id="login-form" onsubmit="submitLogin(event)" novalidate>
        <label class="form-label">Nickname
          <input id="login-nickname" class="form-input" placeholder="Your nickname" required maxlength="30" autocomplete="off"/>
        </label>
        <p id="login-msg" class="form-msg" aria-live="polite"></p>
        <button type="submit" class="btn-primary">Log In</button>
      </form>
      <p class="modal-note">New here? <button class="link-btn" onclick="showRegModal()">Register</button></p>
    </div>
  </div>
</div>`);
}

function showRegModal()   { injectModals(); document.getElementById('reg-modal').style.display   = 'flex'; setTimeout(() => document.getElementById('reg-nickname').focus(), 40); }
function hideRegModal()   { const m = document.getElementById('reg-modal');   if (m) m.style.display = 'none'; }
function showLoginModal() { injectModals(); hideRegModal(); document.getElementById('login-modal').style.display = 'flex'; setTimeout(() => document.getElementById('login-nickname').focus(), 40); }
function hideLoginModal() { const m = document.getElementById('login-modal'); if (m) m.style.display = 'none'; }
// showGroupModal defined below in Cooperative groups section
function hideGroupModal() { const m = document.getElementById('group-modal'); if (m) m.style.display = 'none'; }

// Close modals when clicking the overlay background
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    hideRegModal(); hideLoginModal(); hideGroupModal();
  }
});

// ── Registration ─────────────────────────────────────────────────────────────

async function submitReg(e) {
  e.preventDefault();
  const nickname = document.getElementById('reg-nickname').value.trim();
  const grade    = document.getElementById('reg-grade').value;
  const school        = document.getElementById('reg-school').value.trim();
  const city          = document.getElementById('reg-city').value.trim();
  const parent_email  = document.getElementById('reg-parent-email').value.trim();
  const msg      = document.getElementById('reg-msg');

  if (!nickname || !grade) {
    msg.textContent = 'Please fill in your nickname and grade.';
    msg.className = 'form-msg error';
    return;
  }
  msg.textContent = 'Saving…';
  msg.className = 'form-msg';

  if (!API) {
    saveUser({ userId: crypto.randomUUID(), nickname, grade, school, city });
    hideRegModal(); renderBadge();
    return;
  }

  try {
    const res  = await fetch(`${API}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nickname, grade, school, city, parent_email }),
    });
    const data = await res.json();
    if (!res.ok) {
      msg.textContent = data.error || 'That nickname might already be taken. Try another!';
      msg.className = 'form-msg error';
      return;
    }
    saveUser({ userId: data.userId, nickname: data.nickname, grade: data.grade, school: data.school, city: data.city, parent_email: data.parent_email });
    store.set('dmk_review', []); store.set('doneDays', {});
    hideRegModal(); renderBadge();
    if (typeof showGradeProblems === 'function') showGradeProblems();
    if (typeof resumeOrLockQuiz === 'function') resumeOrLockQuiz();
    loadUserGroup();
    _retryPendingSubmit();
  } catch {
    // Network error — continue as guest so the student can still practice offline
    saveUser({ userId: crypto.randomUUID(), nickname, grade, school, city, parent_email, guest: true });
    store.set('dmk_review', []); store.set('doneDays', {});
    hideRegModal(); renderBadge();
    if (typeof showGradeProblems === 'function') showGradeProblems();
    if (typeof resumeOrLockQuiz === 'function') resumeOrLockQuiz();
    _retryPendingSubmit();
  }
}

// ── Login (returning user) ────────────────────────────────────────────────────

async function submitLogin(e) {
  e.preventDefault();
  const nickname = document.getElementById('login-nickname').value.trim();
  const msg      = document.getElementById('login-msg');
  msg.textContent = 'Looking up…';
  msg.className = 'form-msg';

  if (!API) {
    msg.textContent = 'No API configured – please register.';
    msg.className = 'form-msg error';
    return;
  }

  try {
    const res  = await fetch(`${API}/api/lookup?nickname=${encodeURIComponent(nickname)}`);
    const data = await res.json();
    if (!res.ok) {
      msg.textContent = data.error || 'Nickname not found. Please register first.';
      msg.className = 'form-msg error';
      return;
    }
    saveUser({ userId: data.userId, nickname: data.nickname, grade: data.grade, school: data.school, city: data.city });
    store.set('dmk_review', []); store.set('doneDays', {});
    hideLoginModal(); renderBadge();
    if (typeof showGradeProblems === 'function') showGradeProblems();
    if (typeof resumeOrLockQuiz === 'function') resumeOrLockQuiz();
    loadUserGroup();
    _retryPendingSubmit();
  } catch {
    msg.textContent = 'Could not connect. Please try again.';
    msg.className = 'form-msg error';
  }
}

function _retryPendingSubmit() {
  if (!window._pendingSubmit) return;
  const { quizId, answers, resultEl } = window._pendingSubmit;
  window._pendingSubmit = null;
  resultEl.textContent = 'Checking…';
  submitQuizAnswers(quizId, answers, resultEl);
}

// ── Speed timer ─────────────────────────────────────────────────────────────

function getQuizTimeLimit() {
  const code = window.DMK_ACTIVE_GRADE || 'G3';
  const num = parseInt(code.replace('G', ''), 10) || 3;
  return num <= 5 ? 600 : 900;
}

const dmkTimer = {
  _start: null,
  _seconds: null,
  _limit: null,
  begin(limit) {
    if (!this._start) {
      this._start = Date.now();
      this._limit = limit || getQuizTimeLimit();
      store.set('dmk_timer_start', this._start);
      store.set('dmk_timer_limit', this._limit);
    }
  },
  restore() {
    const saved = store.get('dmk_timer_start', null);
    const limit = store.get('dmk_timer_limit', null);
    if (saved) { this._start = saved; this._limit = limit || getQuizTimeLimit(); return true; }
    return false;
  },
  stop() {
    if (this._start && this._seconds === null)
      this._seconds = Math.round((Date.now() - this._start) / 1000);
    store.set('dmk_timer_start', null);
    store.set('dmk_timer_limit', null);
    return this._seconds;
  },
  elapsed() {
    if (this._seconds !== null) return this._seconds;
    return this._start ? Math.round((Date.now() - this._start) / 1000) : 0;
  },
  remaining() {
    if (!this._limit) return Infinity;
    return Math.max(0, this._limit - this.elapsed());
  },
  isExpired() { return this._limit && this.elapsed() >= this._limit; },
  reset() {
    this._start = null; this._seconds = null; this._limit = null;
    store.set('dmk_timer_start', null);
    store.set('dmk_timer_limit', null);
  },
  fmt(s) { const m = Math.floor(s/60), sec = s%60; return m+':'+String(sec).padStart(2,'0'); },
};

// ── Quiz submission ───────────────────────────────────────────────────────────

async function submitQuizAnswers(quizId, answers, resultEl, timeSeconds) {
  const u = getUser();
  if (!u) {
    window._pendingSubmit = { quizId, answers, resultEl };
    resultEl.textContent = 'Register or log in below to save your score!';
    showRegModal();
    return false;
  }

  if (isQuizExpired()) {
    resultEl.innerHTML = '\uD83D\uDD12 This quiz has expired \u2014 only today\'s quiz can be submitted for points. <a href="../index.html">Go to today\'s quiz!</a>';
    return false;
  }

  if (!API) {
    resultEl.textContent = 'Practice recorded! Keep going! &#x1F600;';
    return true;
  }

  try {
    const res  = await fetch(`${API}/api/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId: u.userId, quizId, answers, timeSeconds: timeSeconds ?? null }),
    });
    const data = await res.json();
    if (!res.ok) {
      resultEl.textContent = data.error || 'Something went wrong. Try again!';
      return false;
    }
    if (data.already) {
      resultEl.innerHTML = `<p>✅ You already completed this quiz today — great job showing up!</p>`;
    } else {
      const perfect  = data.score === data.outOf;
      const pct      = data.outOf > 0 ? data.score / data.outOf : 0;
      const emoji    = perfect ? '🎉' : pct >= 0.6 ? '🌟' : '💪';
      const praise   = perfect
        ? 'Perfect score — you nailed every single one!'
        : pct >= 0.6
        ? `Great effort! ${data.score} out of ${data.outOf} — you showed up and that counts!`
        : `Keep going! ${data.score} out of ${data.outOf} today — every practice makes you stronger!`;
      const shieldAwarded = perfect ? awardShield() : false;
      const shieldNote = shieldAwarded
        ? `<p class="shield-note" style="color:var(--primary);font-weight:700">🛡️ You won a magic shield! It lets you skip one day without losing your streak!</p>`
        : perfect && !shieldAwarded
        ? `<p class="shield-note" style="color:var(--muted)">🛡️ Perfect score! You can earn a new shield next month.</p>`
        : (hasShield() ? `<p class="shield-note" style="color:var(--muted)">🛡️ Your magic shield is ready — you can skip a day and your streak stays safe!</p>` : '');
      const timeNote = timeSeconds ? `<p class="time-taken">&#9201; Completed in <strong>${dmkTimer.fmt(timeSeconds)}</strong></p>` : '';
      let feedbackHtml = '';
      if (data.results && data.results.length) {
        feedbackHtml = '<div class="answer-feedback" style="margin-top:1rem;text-align:left">';
        data.results.forEach(r => {
          const icon = r.correct ? '✅' : '❌';
          const mindsetMsgs = [
            'Mistakes help your brain grow! 🌱',
            'Every wrong answer teaches you something new! 📚',
            'Not yet — but you\'re learning! 🌟',
            'This is how your brain builds new connections! 🧠',
            'Almost! Each attempt makes you smarter! ⭐',
          ];
          const mindset = mindsetMsgs[Math.floor(Math.random() * mindsetMsgs.length)];
          const detail = r.correct
            ? `<span style="color:green">Q${r.question}: Correct!</span>`
            : `<span style="color:red">Q${r.question}: Your answer: <strong>${r.given || '(blank)'}</strong> — Correct: <strong>${r.expected}</strong></span> <span style="font-size:.8rem;color:#2563eb">${mindset}</span>`;
          feedbackHtml += `<p style="margin:0.3rem 0">${icon} ${detail}</p>`;
        });
        feedbackHtml += '</div>';
      }
      resultEl.innerHTML =
        `<div class="result-celebration">` +
        `<p class="result-praise">${emoji} ${praise}</p>` +
        `<p class="points-earned">+${data.points_earned} point${data.points_earned !== 1 ? 's' : ''} earned today!</p>` +
        timeNote +
        feedbackHtml +
        shieldNote +
        (!perfect ? `<button class="btn-secondary" onclick="retryQuiz()">&#9999;&#65039; Try again</button>` : '') +
        `</div>`;
      checkAndRevealFadedHints(quizId, answers);
      saveWrongAnswersForReview(quizId, answers);
      if (typeof addSolvedQuestions === 'function') addSolvedQuestions(answers.length);
    }
    return data;
  } catch {
    resultEl.textContent = 'Could not reach the server. Keep practising!';
    return false;
  }
}

// ── Cooperative groups ────────────────────────────────────────────────────────

async function loadUserGroup() {
  const u = getUser();
  if (!u || !API) return;
  try {
    const res = await fetch(`${API}/api/groups?userId=${encodeURIComponent(u.userId)}`);
    const data = await res.json();
    if (data.group) store.set('dmk_group', data.group);
    else store.set('dmk_group', null);
  } catch {}
}

async function showGroupModal() {
  injectModals();
  const modal = document.getElementById('group-modal');
  const msg   = document.getElementById('group-msg');
  modal.style.display = 'flex';

  // Fetch fresh group data
  const u = getUser();
  if (u && API) {
    msg.textContent = 'Loading group…';
    msg.className = 'form-msg';
    await loadUserGroup();
  }

  const g = store.get('dmk_group', null);
  if (g && g.groupName) {
    let html = `<div style="text-align:left">` +
      `<h3 style="margin:0 0 6px">🤝 ${escHtml(g.groupName)}</h3>` +
      (g.invite_code ? `<p style="margin:4px 0">Invite code: <strong style="font-size:1.2rem;letter-spacing:2px;color:var(--primary)">${g.invite_code}</strong></p>` : '') +
      `<p style="margin:4px 0;color:var(--muted)">${g.member_count ?? 0} members · ${g.total_points ?? 0} total pts · ${g.quizzes_completed ?? 0} quizzes</p>`;
    if (g.members && g.members.length > 0) {
      html += `<table style="width:100%;border-collapse:collapse;margin:10px 0;font-size:.9rem">` +
        `<thead><tr style="border-bottom:2px solid var(--border,#e0e0e0);text-align:left">` +
        `<th style="padding:6px 8px">Member</th><th style="padding:6px 8px">Grade</th>` +
        `<th style="padding:6px 8px">Points</th><th style="padding:6px 8px">Quizzes</th><th style="padding:6px 8px">Perfect</th></tr></thead><tbody>`;
      g.members.forEach(m => {
        html += `<tr style="border-bottom:1px solid var(--border,#eee)">` +
          `<td style="padding:6px 8px;font-weight:600">${escHtml(m.nickname)}</td>` +
          `<td style="padding:6px 8px">${m.grade || '—'}</td>` +
          `<td style="padding:6px 8px">${m.totalPoints}</td>` +
          `<td style="padding:6px 8px">${m.quizzes}</td>` +
          `<td style="padding:6px 8px">${m.perfect > 0 ? '⭐ ' + m.perfect : '—'}</td></tr>`;
      });
      html += `</tbody></table>`;
    }
    html += `</div>`;
    msg.innerHTML = html;
    msg.className = 'form-msg';
  } else {
    msg.textContent = '';
  }
  setTimeout(() => document.getElementById('group-name-input')?.focus(), 40);
}

async function createGroup() {
  const u    = getUser();
  const msg  = document.getElementById('group-msg');
  const name = document.getElementById('group-name-input')?.value.trim();
  if (!u) { showRegModal(); return; }
  if (!name) { msg.textContent = 'Please enter a group name.'; msg.className = 'form-msg error'; return; }
  msg.textContent = 'Creating…'; msg.className = 'form-msg';
  try {
    const res  = await fetch(`${API}/api/groups`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'create', userId: u.userId, groupName: name }),
    });
    const data = await res.json();
    if (!res.ok) { msg.textContent = data.error || 'Could not create group.'; msg.className = 'form-msg error'; return; }
    store.set('dmk_group', data);
    msg.innerHTML = `✅ Group created! Share this code with your family/class: <strong style="font-size:1.3rem;letter-spacing:2px">${data.invite_code}</strong>`;
    msg.className = 'form-msg';
  } catch { msg.textContent = 'Could not connect. Try again.'; msg.className = 'form-msg error'; }
}

async function joinGroup() {
  const u    = getUser();
  const msg  = document.getElementById('group-msg');
  const code = document.getElementById('group-code-input')?.value.trim().toUpperCase();
  if (!u) { showRegModal(); return; }
  if (!code) { msg.textContent = 'Please enter an invite code.'; msg.className = 'form-msg error'; return; }
  msg.textContent = 'Joining…'; msg.className = 'form-msg';
  try {
    const res  = await fetch(`${API}/api/groups`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'join', userId: u.userId, invite_code: code }),
    });
    const data = await res.json();
    if (!res.ok) { msg.textContent = data.error || 'Could not join group.'; msg.className = 'form-msg error'; return; }
    store.set('dmk_group', data);
    msg.innerHTML = `🎉 Joined <strong>${escHtml(data.groupName)}</strong>! ${data.member_count} members, ${data.total_points} pts so far.`;
    msg.className = 'form-msg';
  } catch { msg.textContent = 'Could not connect. Try again.'; msg.className = 'form-msg error'; }
}

// ── Retry quiz ────────────────────────────────────────────────────────────────

function retryQuiz() {
  const form     = document.getElementById('quiz');
  const resultEl = document.getElementById('result');
  const streakEl = document.getElementById('streak-msg');
  if (resultEl) resultEl.innerHTML = '<p class="retry-nudge">✏️ Hints are now visible — give it another go!</p>';
  if (streakEl) streakEl.textContent = '';
  if (form) {
    form.querySelectorAll('input[type=text],input:not([type])').forEach(inp => inp.value = '');
    form.style.display = 'block';
  }
}

// ── Feelings check-in ─────────────────────────────────────────────────────────

function renderFeelingsCheckin(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const todayKey = 'dmk_feeling_' + new Date().toISOString().slice(0, 10);
  const stored   = store.get(todayKey);
  if (stored) { el.style.display = 'none'; return; }
  el.innerHTML =
    `<div class="feelings-bar">
      <span>How are you feeling about today's math?</span>
      <button class="feeling-btn" onclick="recordFeeling('calm',this)">😊 Calm</button>
      <button class="feeling-btn" onclick="recordFeeling('unsure',this)">😐 Unsure</button>
      <button class="feeling-btn" onclick="recordFeeling('stressed',this)">😰 Stressed</button>
    </div>`;
}

function recordFeeling(feeling, btn) {
  const todayKey = 'dmk_feeling_' + new Date().toISOString().slice(0, 10);
  store.set(todayKey, feeling);
  const bar = btn.closest('.feelings-bar');
  if (feeling === 'stressed') {
    bar.innerHTML = `<p class="feelings-response">💙 That's okay — take a breath. Start with Problem 1 and use the hint if you need it. You've got this!</p>`;
    const grade = window.DMK_ACTIVE_GRADE || 'G3';
    const sec   = document.querySelector(`.grade-section[data-grade="${grade}"]`);
    const firstHintBtn = (sec || document).querySelector('.hint-wrap');
    if (firstHintBtn) firstHintBtn.open = true;
  } else if (feeling === 'unsure') {
    bar.innerHTML = `<p class="feelings-response">👍 That's normal! Hints and steps are there to help — give it your best shot!</p>`;
  } else {
    bar.innerHTML = `<p class="feelings-response">🌟 Love the energy! Let's go!</p>`;
  }
}

// ── Grade helpers ───────────────────────────────────────────────────────────

function gradeToCode(grade) {
  const m = String(grade || '').match(/(\d+)/);
  return m ? 'G' + m[1] : 'G3';
}

function isQuizExpired() {
  if (typeof QUIZ_DATE === 'undefined') return false;
  const today = new Date().toISOString().slice(0, 10);
  return QUIZ_DATE !== today;
}

function showGradeProblems() {
  const u    = getUser();
  const code = gradeToCode(u ? u.grade : store.get('dmk_lvl') || 'G3');
  window.DMK_ACTIVE_GRADE = code;
  const expired = isQuizExpired();
  document.querySelectorAll('.grade-section').forEach(el => {
    if (el.dataset.grade === code) {
      el.style.display = 'block';
      if (expired) {
        el.style.filter = 'none';
        el.style.pointerEvents = 'auto';
        el.style.userSelect = 'auto';
        el.style.opacity = '1';
      } else {
        el.style.filter = 'blur(6px)';
        el.style.pointerEvents = 'none';
        el.style.userSelect = 'none';
      }
    } else {
      el.style.display = 'none';
    }
  });
  if (typeof QUIZ_DATE !== 'undefined') window.QUIZ_ID = QUIZ_DATE + '-' + code;
  const notice = document.getElementById('grade-notice');
  if (notice) notice.textContent = `Grade ${code.replace('G', '')} problems`;
  const helloEl = document.getElementById('hello');

  if (expired) {
    if (helloEl) helloEl.innerHTML = '\uD83D\uDD12 This quiz has expired. You can review the questions, but only today\'s quiz earns points. <a href="../index.html">Go to today\'s quiz!</a>';
    const submitBtn = document.querySelector('#quiz button[type="submit"]');
    if (submitBtn) { submitBtn.disabled = true; submitBtn.style.opacity = '0.5'; submitBtn.textContent = 'Quiz Expired'; }
    return;
  }

  if (helloEl && u) helloEl.textContent = `Grade ${code.replace('G', '')} problems — press Start Test to begin!`;
  if (helloEl && !u) helloEl.textContent = 'Sign up or log in to start the quiz!';

  // Show start test button above the grade sections (top of page)
  let startBtn = document.getElementById('start-test-btn');
  if (!startBtn) {
    startBtn = document.createElement('button');
    startBtn.id = 'start-test-btn';
    startBtn.type = 'button';
    startBtn.textContent = '▶ Start Test';
    startBtn.style.cssText = 'display:block;margin:16px auto;padding:14px 40px;font-size:1.2rem;font-weight:700;background:var(--primary);color:#fff;border:none;border-radius:var(--radius-pill,24px);cursor:pointer;font-family:inherit;box-shadow:0 4px 12px rgba(37,99,235,.3)';
    // Insert before the first grade-section so it appears at the top
    const firstSection = document.querySelector('.grade-section');
    if (firstSection) firstSection.parentNode.insertBefore(startBtn, firstSection);
  }
  startBtn.style.display = 'block';
}

function getQuizState(qid) {
  return store.get('dmk_quiz_state_' + qid, null);
}
function setQuizState(qid, state) {
  store.set('dmk_quiz_state_' + qid, state);
}

function startTest() {
  const u = getUser();
  if (!u) {
    showRegModal();
    return;
  }
  const code = window.DMK_ACTIVE_GRADE || 'G3';
  const qid = window.QUIZ_ID || (typeof QUIZ_ID !== 'undefined' ? QUIZ_ID : '');
  setQuizState(qid, 'started');
  store.set('dmk_active_quiz_url', window.location.href);
  _revealTest(code);
}

function _revealTest(code) {
  const section = document.querySelector(`.grade-section[data-grade="${code}"]`);
  if (section) {
    section.style.filter = 'none';
    section.style.pointerEvents = 'auto';
    section.style.userSelect = 'auto';
  }
  const startBtn = document.getElementById('start-test-btn');
  if (startBtn) startBtn.style.display = 'none';
  const helloEl = document.getElementById('hello');
  const limit = dmkTimer._limit || getQuizTimeLimit();
  const mins = Math.floor(limit / 60);
  if (helloEl) helloEl.textContent = `Grade ${code.replace('G', '')} — ${mins} minutes to finish. Select your answers and submit!`;
  if (typeof _startTimerUI === 'function') _startTimerUI();
}

function _lockQuizDone(code) {
  const section = document.querySelector(`.grade-section[data-grade="${code}"]`);
  if (section) {
    section.style.filter = 'none';
    section.style.pointerEvents = 'none';
    section.style.userSelect = 'none';
    section.style.opacity = '0.6';
  }
  const startBtn = document.getElementById('start-test-btn');
  if (startBtn) startBtn.style.display = 'none';
  const helloEl = document.getElementById('hello');
  if (helloEl) helloEl.innerHTML = '✅ You already completed this quiz! <a href="../index.html">Back to Home</a>';
  const submitBtn = document.querySelector('#quiz button[type="submit"]');
  if (submitBtn) { submitBtn.disabled = true; submitBtn.style.opacity = '0.5'; submitBtn.textContent = 'Already Submitted'; }
}

function resumeOrLockQuiz() {
  const qid = window.QUIZ_ID || (typeof QUIZ_ID !== 'undefined' ? QUIZ_ID : '');
  if (!qid) return;
  const code = qid.replace(/^.*-(G\d+)$/, '$1');
  const state = getQuizState(qid);
  if (state === 'done') {
    _lockQuizDone(code);
  } else if (state === 'started') {
    dmkTimer.restore();
    if (dmkTimer.isExpired()) {
      _autoSubmitQuiz();
      return;
    }
    _revealTest(code);
  }
}

function checkForActiveQuizRedirect() {
  if (typeof QUIZ_DATE !== 'undefined') return;
  const url = store.get('dmk_active_quiz_url', null);
  if (!url) return;
  const today = new Date().toISOString().slice(0, 10);
  if (!url.includes(today)) {
    store.set('dmk_active_quiz_url', null);
    return;
  }
  const keys = Object.keys(localStorage).filter(k => k.startsWith('dmk_quiz_state_') && k.includes(today));
  const hasActive = keys.some(k => localStorage.getItem(k) === '"started"');
  if (hasActive) {
    const banner = document.createElement('div');
    banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;background:#dc2626;color:#fff;padding:14px 20px;text-align:center;font-weight:700;font-size:1.1rem;box-shadow:0 4px 12px rgba(0,0,0,.2)';
    banner.innerHTML = '\u23F0 You have an active quiz in progress! <a href="' + url + '" style="color:#fff;text-decoration:underline;margin-left:8px">Go back to finish it</a>';
    document.body.prepend(banner);
  }
}

function lockAnswersAfterSubmit() {
  document.querySelectorAll('.mc-btn').forEach(btn => {
    btn.disabled = true;
    btn.style.cursor = 'default';
    btn.style.opacity = '0.7';
  });
  const submitBtn = document.querySelector('#quiz button[type="submit"]');
  if (submitBtn) { submitBtn.disabled = true; submitBtn.style.opacity = '0.5'; }
}

function showCompletionAndRedirect(score) {
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,.6);display:flex;align-items:center;justify-content:center;z-index:2000;padding:16px';
  const perfect = score === 5;
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:20px;padding:32px 28px;max-width:420px;width:100%;text-align:center;box-shadow:0 12px 40px rgba(0,0,0,.2)">
      <div style="font-size:3rem;margin-bottom:12px">${perfect ? '🎉' : '✅'}</div>
      <h2 style="margin:0 0 8px;font-size:1.5rem">${perfect ? 'Perfect Score!' : 'Quiz Complete!'}</h2>
      <p style="color:#64748b;margin:0 0 16px">${perfect ? 'Amazing! You got all 5 correct!' : 'Great effort! Every problem you try makes your brain stronger. Come back tomorrow! 💪'}</p>
      <p style="font-size:1.1rem;font-weight:700;color:#2563eb;margin:0 0 20px">+${score} point${score !== 1 ? 's' : ''}${perfect ? ' + 3 bonus!' : ''}</p>
      <a href="${ROOT || './'}index.html" style="display:inline-block;background:#2563eb;color:#fff;padding:12px 32px;border-radius:999px;font-weight:700;text-decoration:none;font-size:1rem">Back to Home</a>
    </div>`;
  document.body.appendChild(overlay);
}

// ── Hint reveal ──────────────────────────────────────────────────────────────────

function trackWrongAnswer(quizId, qNum) {
  const key = 'dmk_wrong_' + quizId;
  const d   = store.get(key, {});
  d[qNum]   = (d[qNum] || 0) + 1;
  store.set(key, d);
  return d[qNum];
}

function revealFadedHint(qNum, wrongCount) {
  const grade   = window.DMK_ACTIVE_GRADE || 'G3';
  const section = document.querySelector(`.grade-section[data-grade="${grade}"]`);
  const li = (section || document).querySelectorAll('.problems-list li')[qNum - 1];
  if (!li) return;
  if (wrongCount >= 1) {
    const hintEl = li.querySelector('.hint-wrap');
    if (hintEl) hintEl.open = true;
  }
  if (wrongCount >= 2) {
    const stepsEl = li.querySelector('.steps-wrap');
    if (stepsEl) stepsEl.open = true;
  }
}

function checkAndRevealFadedHints(quizId, answers) {
  const grade   = window.DMK_ACTIVE_GRADE || 'G3';
  const section = document.querySelector(`.grade-section[data-grade="${grade}"]`);
  const problems = (section || document).querySelectorAll('.problems-list li');
  answers.forEach((ans, i) => {
    const li      = problems[i];
    if (!li) return;
    const correct = (li.dataset.answer || '').trim();
    if (correct && String(ans).trim() !== correct) {
      const count = trackWrongAnswer(quizId, i + 1);
      revealFadedHint(i + 1, count);
    }
  });
}

// ── Review questions ───────────────────────────────────────────────────────────

function saveWrongAnswersForReview(quizId, answers) {
  const grade   = window.DMK_ACTIVE_GRADE || 'G3';
  const section = document.querySelector(`.grade-section[data-grade="${grade}"]`);
  const problems = (section || document).querySelectorAll('.problems-list li');
  const items    = store.get('dmk_review', []);
  answers.forEach((ans, i) => {
    const li      = problems[i];
    if (!li) return;
    const correct = (li.dataset.answer || '').trim();
    const qText   = li.dataset.question || li.querySelector('.problem-en')?.textContent || '';
    if (correct && String(ans).trim() !== correct && qText) {
      const filtered = items.filter(x => !(x.quizId === quizId && x.qNum === i + 1));
      filtered.push({ quizId, qNum: i + 1, questionText: qText, answer: correct, date: new Date().toISOString().slice(0, 10) });
      items.length = 0;
      items.push(...filtered.slice(-30));
    }
  });
  store.set('dmk_review', items);
}

function renderReviewSection(containerId) {
  const el    = document.getElementById(containerId);
  if (!el) return;
  const all   = store.get('dmk_review', []);
  const today = new Date().toISOString().slice(0, 10);
  const due   = all.filter(x => x.date < today).slice(-3);
  if (!due.length) { el.style.display = 'none'; return; }
  el.innerHTML =
    `<div class="review-section">
      <h3>🔁 Review from earlier</h3>
      <p class="review-sub">These gave you trouble before — try them again!</p>
      <ol>${due.map(it =>
        `<li>
          <p>${escHtml(it.questionText)}</p>
          <details class="steps-wrap"><summary>Show answer</summary>
            <p><strong>${escHtml(it.answer)}</strong></p>
          </details>
        </li>`).join('')}
      </ol>
    </div>`;
}

// ── Streaks ───────────────────────────────────────────────────────────────────

function markDayDone(slug) {
  const d = store.get('doneDays', {});
  d[slug] = true;
  store.set('doneDays', d);
}

function hasShield()   { return store.get('dmk_shield', false) === true; }
function awardShield() {
  const lastEarned = store.get('dmk_shield_date', null);
  if (lastEarned) {
    const daysSince = Math.floor((Date.now() - new Date(lastEarned).getTime()) / 86400000);
    if (daysSince < 30) return false; // max one shield per month
  }
  store.set('dmk_shield', true);
  store.set('dmk_shield_date', new Date().toISOString().slice(0, 10));
  return true;
}
function consumeShield() { store.set('dmk_shield', false); }

function calcStreak(slug) {
  const d  = store.get('doneDays', {});
  let s = 0, shieldUsed = false;
  const dt = new Date(slug);
  for (;;) {
    const key = dt.toISOString().slice(0, 10);
    if (d[key]) {
      s++;
      dt.setDate(dt.getDate() - 1);
    } else if (!shieldUsed && hasShield()) {
      shieldUsed = true;
      consumeShield();
      dt.setDate(dt.getDate() - 1);
    } else {
      break;
    }
  }
  return s;
}

// ── Daily reminders ────────────────────────────────────────────────────────────

function registerSW() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register((window.DMK_ROOT || './') + 'scripts/sw.js')
      .catch(() => {});
  }
}

async function enableReminders(btnEl) {
  if (!('Notification' in window)) {
    alert('Your browser does not support notifications.');
    return;
  }
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    if (btnEl) { btnEl.textContent = '🔕 Notifications blocked'; btnEl.disabled = true; }
    return;
  }
  store.set('dmk_reminders', true);
  if (btnEl) { btnEl.textContent = '✅ Reminders on!'; btnEl.disabled = true; btnEl.className = 'reminder-btn on'; }

  if ('serviceWorker' in navigator && 'periodicSync' in (await navigator.serviceWorker.ready)) {
    try {
      const reg = await navigator.serviceWorker.ready;
      await reg.periodicSync.register('dmk-daily-reminder', { minInterval: 24 * 60 * 60 * 1000 });
    } catch {}
  }

  new Notification('🧮 Daily Math for Kids', {
    body: "You're all set! We'll remind you every day to keep your streak going 🔥",
    icon: (window.DMK_ROOT || './') + 'favicon.ico',
    tag: 'dmk-confirm',
  });
}

function checkDailyReminder() {
  if (!store.get('dmk_reminders')) return;
  if (Notification.permission !== 'granted') return;
  const today  = new Date().toISOString().slice(0, 10);
  const done   = store.get('doneDays', {});
  const hour   = new Date().getHours();
  const shown  = store.get('dmk_reminder_shown_' + today);
  if (!done[today] && hour >= 15 && !shown) {
    store.set('dmk_reminder_shown_' + today, true);
    new Notification('🧮 Daily Math for Kids', {
      body: "You haven't done today's problems yet — keep your streak alive! 🔥",
      icon: (window.DMK_ROOT || './') + 'favicon.ico',
      tag: 'dmk-daily',
    });
  }
}

function renderReminderButton(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const on = store.get('dmk_reminders') && Notification.permission === 'granted';
  el.innerHTML =
    `<button class="reminder-btn ${on ? 'on' : ''}" onclick="enableReminders(this)" ${on ? 'disabled' : ''}>` +
    (on ? '✅ Daily reminders on' : '🔔 Enable daily reminders') +
    `</button>`;
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  registerSW();
  injectModals();
  renderBadge();
  checkDailyReminder();
  checkForActiveQuizRedirect();
});
