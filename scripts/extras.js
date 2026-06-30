/* ══════════════════════════════════════════════════════════
   extras.js — Dark mode, mascot, welcome confetti
   ══════════════════════════════════════════════════════════ */

// ── Dark Mode Toggle ────────────────────────────────────
(function initDarkMode() {
  var saved = localStorage.getItem('dmk_theme');
  if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');

  var btn = document.createElement('button');
  btn.className = 'theme-toggle';
  btn.setAttribute('aria-label', 'Toggle dark mode');
  btn.title = 'Toggle dark/light mode';
  btn.textContent = saved === 'dark' ? '☀️' : '🌙';
  btn.addEventListener('click', function() {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (isDark) {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('dmk_theme', 'light');
      btn.textContent = '🌙';
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('dmk_theme', 'dark');
      btn.textContent = '☀️';
    }
  });
  document.body.appendChild(btn);
})();

// ── Mascot ──────────────────────────────────────────────
(function initMascot() {
  var tips = [
    'Math is a superpower! 💪',
    'Practice makes perfect! ⭐',
    'You\'re doing great! 🎉',
    'Try today\'s quiz! 📝',
    'Mistakes help you learn! 🧠',
    'Keep going, champ! 🏆',
    'Every day counts! 📅',
    'Numbers are fun! 🔢',
    'Believe in yourself! ✨',
    'Ready for a challenge? 🚀',
    'You\'re a math star! 🌟',
    'Stay curious! 🔍',
  ];

  var mascot = document.createElement('div');
  mascot.className = 'mascot';
  mascot.setAttribute('role', 'img');
  mascot.setAttribute('aria-label', 'Math mascot');
  mascot.textContent = '🧮';

  var speech = document.createElement('div');
  speech.className = 'mascot-speech';
  speech.textContent = tips[0];

  var tipIndex = 0;
  var hideTimer;

  function showTip() {
    speech.textContent = tips[tipIndex];
    speech.classList.add('show');
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function() { speech.classList.remove('show'); }, 3500);
    tipIndex = (tipIndex + 1) % tips.length;
  }

  mascot.addEventListener('click', showTip);

  // Show a welcome tip after a short delay
  setTimeout(function() {
    showTip();
    // Auto-rotate tips every 15 seconds
    setInterval(showTip, 15000);
  }, 2000);

  document.body.appendChild(speech);
  document.body.appendChild(mascot);
})();

// ── Welcome Confetti ────────────────────────────────────
(function initWelcomeConfetti() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  // Only show once per session
  if (sessionStorage.getItem('dmk_welcomed')) return;
  sessionStorage.setItem('dmk_welcomed', '1');

  // Load confetti if not already loaded
  function fire() {
    if (typeof confetti !== 'function') return;
    // Two bursts from both sides
    confetti({ particleCount: 60, spread: 70, origin: { x: 0.15, y: 0.6 }, colors: ['#6366f1','#10b981','#f59e0b','#ec4899','#06b6d4'] });
    confetti({ particleCount: 60, spread: 70, origin: { x: 0.85, y: 0.6 }, colors: ['#8b5cf6','#f43f5e','#14b8a6','#f97316','#84cc16'] });
    // A third center burst slightly delayed
    setTimeout(function() {
      confetti({ particleCount: 40, spread: 100, origin: { x: 0.5, y: 0.5 }, colors: ['#6366f1','#ec4899','#f59e0b','#10b981'] });
    }, 300);
  }

  if (typeof confetti === 'function') {
    setTimeout(fire, 500);
  } else {
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js';
    s.onload = function() { setTimeout(fire, 300); };
    document.head.appendChild(s);
  }
})();
