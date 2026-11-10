const { execFileSync } = require('child_process');
const path = require('path');

function fixture(day) {
  return JSON.parse(execFileSync('python', ['-c', `
import json, sys
sys.path.insert(0, 'scripts')
from daily_challenges import challenge_markdown, make_challenge
from gen_site import generate_html_from_text, HELPERS_JS
text = '\\n'.join('## G' + str(g) + '\\n' + '\\n'.join(
    challenge_markdown(g, '${day}', slot).replace('0.', str(slot + 1) + '.', 1)
    for slot in range(2)
) for g in range(1, 13))
print(json.dumps({
 'page': generate_html_from_text(text, '${day}'),
 'helpers': HELPERS_JS,
 'answers': [make_challenge(g, '${day}', slot)['answer'] for g in range(1, 13) for slot in range(2)],
}))
`], { encoding: 'utf8', cwd: path.join(__dirname, '..') }));
}

test('challenge generation and mathematical invariants pass Python checks', () => {
  expect(() => execFileSync('python', ['-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_daily_challenges.py'], {
    cwd: path.join(__dirname, '..'), stdio: 'pipe',
  })).not.toThrow();
});

beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'innerText', {
    configurable: true,
    get() { return this.innerHTML.replace(/<[^>]*>/g, '\n'); },
  });
});

test.each(['2026-11-02', '2026-11-03'])('two challenge diagrams and choices survive enhancement on %s', day => {
  const data = fixture(day);
  document.body.innerHTML = data.page;
  window.eval(data.helpers.replace(/^\s*<script>/, '').replace(/<\/script>\s*$/, ''));
  const items = document.querySelectorAll('.problems-list > li');
  expect(items).toHaveLength(24);
  expect(document.querySelectorAll('svg.challenge-diagram')).toHaveLength(24);
  items.forEach((li, idx) => {
    expect(li.dataset.answer).toBe(data.answers[idx]);
    expect(li.dataset.question).not.toContain('Diagram:');
    expect(li.querySelectorAll('.mc-btn')).toHaveLength(4);
    const correct = [...li.querySelectorAll('.mc-btn')].find(btn => btn.dataset.value === data.answers[idx]);
    expect(correct).toBeDefined();
    correct.click();
    expect(li.dataset.selected).toBe(data.answers[idx]);
    expect(li.querySelector('svg').getAttribute('aria-label')).toBe(li.dataset.question);
  });
});
