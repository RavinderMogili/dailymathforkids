const fs = require('fs');
const path = require('path');
const rules = require('./grade-practice.js');

describe('Official Grade and Practice Grade UI rules', () => {
  test('normalizes supported grade formats', () => {
    expect(rules.formatGrade('G5')).toBe('Grade 5');
    expect(rules.formatGrade('Grade 12')).toBe('Grade 12');
  });

  test('same-grade Practice is points eligible', () => {
    expect(rules.gradesMatch('Grade 5', '5')).toBe(true);
    expect(rules.eligibilityMessage('Grade 5', 'Grade 5')).toMatch(/Points eligible/);
  });

  test('cross-grade Practice is clearly Extra Practice', () => {
    expect(rules.gradesMatch('Grade 5', 'Grade 6')).toBe(false);
    expect(rules.eligibilityMessage('Grade 5', 'Grade 6')).toBe('Extra Practice — no Math Stars points.');
  });

  test('server status copy describes remaining points and cap', () => {
    expect(rules.statusMessage(4)).toBe('6 points still available today');
    expect(rules.statusMessage(10)).toMatch(/all 10 Practice Points/);
  });

  test('Practice page has no local points authority or client pointsEarned field', () => {
    const html = fs.readFileSync(path.join(__dirname, '..', 'practice.html'), 'utf8');
    expect(html).not.toContain('dmk_practice_pts_');
    expect(html).not.toMatch(/pointsEarned\s*,/);
    expect(html).toContain('/api/practice-status');
    expect(html).toContain('practiceGrade');
  });

  test('profile correction uses its dedicated endpoint and has no local grade fallback', () => {
    const html = fs.readFileSync(path.join(__dirname, '..', 'profile.html'), 'utf8');
    const gradeFlow = html.slice(html.indexOf('async function saveGrade'), html.indexOf('// ── Mistake History'));
    expect(html).toContain('/api/grade-correction');
    expect(gradeFlow).not.toContain('Saved locally');
    expect(gradeFlow).not.toContain('/api/register');
  });
});
