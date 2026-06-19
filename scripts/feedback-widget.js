// Floating Feedback Widget — appears on every page
(function() {
  const API = (window.DMK_API || '').replace(/\/$/, '');
  if (!API) return;

  // Inject styles
  const style = document.createElement('style');
  style.textContent = `
    #dmk-feedback-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 9990;
      background: linear-gradient(135deg, #2563eb, #7c3aed);
      color: #fff; border: none; border-radius: 50px;
      padding: 14px 20px; font-size: .95rem; font-weight: 700;
      cursor: pointer; box-shadow: 0 4px 20px rgba(37,99,235,.35);
      transition: transform .2s, box-shadow .2s;
      display: flex; align-items: center; gap: 6px;
    }
    #dmk-feedback-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 24px rgba(37,99,235,.45); }
    #dmk-feedback-panel {
      position: fixed; bottom: 90px; right: 24px; z-index: 9991;
      width: 340px; max-width: calc(100vw - 40px);
      background: #fff; border-radius: 16px;
      box-shadow: 0 10px 40px rgba(0,0,0,.18);
      display: none; flex-direction: column;
      animation: dmk-fb-slide .25s ease;
    }
    @keyframes dmk-fb-slide { from { opacity:0; transform: translateY(12px); } to { opacity:1; transform: translateY(0); } }
    #dmk-feedback-panel.open { display: flex; }
    #dmk-feedback-panel header {
      padding: 16px 20px; border-bottom: 1px solid #f1f5f9;
      display: flex; justify-content: space-between; align-items: center;
    }
    #dmk-feedback-panel header h3 { margin: 0; font-size: 1rem; color: #1e293b; }
    #dmk-feedback-panel header button {
      background: none; border: none; font-size: 1.3rem; cursor: pointer; color: #64748b;
    }
    #dmk-feedback-panel .fb-body { padding: 16px 20px; }
    #dmk-feedback-panel .fb-categories {
      display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px;
    }
    #dmk-feedback-panel .fb-cat {
      padding: 6px 12px; border-radius: 20px; border: 1.5px solid #e2e8f0;
      background: #fff; font-size: .82rem; cursor: pointer; transition: all .15s;
    }
    #dmk-feedback-panel .fb-cat.active {
      background: #2563eb; color: #fff; border-color: #2563eb;
    }
    #dmk-feedback-panel textarea {
      width: 100%; min-height: 80px; border: 1.5px solid #e2e8f0;
      border-radius: 10px; padding: 10px 12px; font-size: .9rem;
      resize: vertical; font-family: inherit; margin-bottom: 10px;
    }
    #dmk-feedback-panel textarea:focus { outline: none; border-color: #2563eb; }
    #dmk-feedback-panel input[type="email"] {
      width: 100%; border: 1.5px solid #e2e8f0; border-radius: 10px;
      padding: 8px 12px; font-size: .85rem; margin-bottom: 12px; font-family: inherit;
    }
    #dmk-feedback-panel input[type="email"]:focus { outline: none; border-color: #2563eb; }
    #dmk-feedback-panel .fb-submit {
      width: 100%; padding: 12px; border: none; border-radius: 10px;
      background: linear-gradient(135deg, #2563eb, #7c3aed);
      color: #fff; font-weight: 700; font-size: .95rem; cursor: pointer;
      transition: opacity .2s;
    }
    #dmk-feedback-panel .fb-submit:disabled { opacity: .5; cursor: not-allowed; }
    #dmk-feedback-panel .fb-success {
      text-align: center; padding: 30px 20px;
    }
    #dmk-feedback-panel .fb-success .checkmark { font-size: 2.5rem; margin-bottom: 8px; }
    @media (max-width: 400px) {
      #dmk-feedback-panel { right: 10px; bottom: 80px; width: calc(100vw - 20px); }
      #dmk-feedback-btn { bottom: 16px; right: 16px; padding: 12px 16px; font-size: .85rem; }
    }
  `;
  document.head.appendChild(style);

  // Create button
  const btn = document.createElement('button');
  btn.id = 'dmk-feedback-btn';
  btn.innerHTML = '💬 Feedback';
  document.body.appendChild(btn);

  // Create panel
  const panel = document.createElement('div');
  panel.id = 'dmk-feedback-panel';
  panel.innerHTML = `
    <header>
      <h3>Share Your Feedback</h3>
      <button id="dmk-fb-close">&times;</button>
    </header>
    <div class="fb-body">
      <div class="fb-categories">
        <span class="fb-cat active" data-cat="suggestion">💡 Suggestion</span>
        <span class="fb-cat" data-cat="bug">🐛 Bug</span>
        <span class="fb-cat" data-cat="question">❓ Question</span>
        <span class="fb-cat" data-cat="wrong_answer">❌ Wrong Answer</span>
      </div>
      <textarea id="dmk-fb-msg" placeholder="Tell us what's on your mind..."></textarea>
      <input type="email" id="dmk-fb-email" placeholder="Your email (optional — for follow-up)"/>
      <button class="fb-submit" id="dmk-fb-submit">Send Feedback</button>
    </div>
  `;
  document.body.appendChild(panel);

  // State
  let selectedCat = 'suggestion';

  // Toggle panel
  btn.addEventListener('click', () => {
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) btn.innerHTML = '✕ Close';
    else btn.innerHTML = '💬 Feedback';
  });
  document.getElementById('dmk-fb-close').addEventListener('click', () => {
    panel.classList.remove('open');
    btn.innerHTML = '💬 Feedback';
  });

  // Category selection
  panel.querySelectorAll('.fb-cat').forEach(el => {
    el.addEventListener('click', () => {
      panel.querySelectorAll('.fb-cat').forEach(c => c.classList.remove('active'));
      el.classList.add('active');
      selectedCat = el.dataset.cat;
    });
  });

  // Submit
  document.getElementById('dmk-fb-submit').addEventListener('click', async () => {
    const msg = document.getElementById('dmk-fb-msg').value.trim();
    if (!msg) { document.getElementById('dmk-fb-msg').focus(); return; }

    const submitBtn = document.getElementById('dmk-fb-submit');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';

    const u = (typeof getUser === 'function') ? getUser() : null;
    try {
      const res = await fetch(`${API}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: u ? u.userId : null,
          category: selectedCat,
          message: msg,
          email: document.getElementById('dmk-fb-email').value.trim() || null,
          pageUrl: window.location.href,
        }),
      });
      if (res.ok) {
        panel.querySelector('.fb-body').innerHTML = `
          <div class="fb-success">
            <div class="checkmark">✅</div>
            <h3 style="margin:8px 0;color:#16a34a">Thank you!</h3>
            <p style="color:#64748b;font-size:.9rem">Your feedback has been received. We appreciate you helping us improve!</p>
          </div>
        `;
        setTimeout(() => {
          panel.classList.remove('open');
          btn.innerHTML = '💬 Feedback';
          // Reset form after close
          setTimeout(() => { location.reload(); }, 300);
        }, 2500);
      } else {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send Feedback';
        alert('Something went wrong. Please try again.');
      }
    } catch {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Send Feedback';
      alert('Network error. Please try again.');
    }
  });
})();
