/**
 * Unit tests for quiz answer validation scenarios.
 * Covers: stripped fractions, stripped currency, stripped time,
 * non-integer division, answer-choice mismatch, missing fields.
 *
 * Run with: npm run test:unit
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Helper: run validate_quiz.py's logic via a Python subprocess on inline markdown
function validateMd(md) {
  const runnerPath = path.join(os.tmpdir(), '_validate_quiz_runner.py');
  const runner = `
import sys, json
sys.path.insert(0, r'${path.join(__dirname).replace(/\\/g, '\\\\')}')
from validate_quiz import parse_questions_from_md, validate_questions
text = sys.stdin.read()
questions = parse_questions_from_md(text)
issues = validate_questions(questions)
result = [{'level': i.level, 'grade': i.grade, 'qnum': i.qnum, 'msg': i.msg, 'fix': i.fix} for i in issues]
print(json.dumps(result))
`;
  fs.writeFileSync(runnerPath, runner, 'utf-8');
  try {
    const out = execSync(`python "${runnerPath}"`, {
      input: md,
      encoding: 'utf-8',
      cwd: __dirname,
    });
    return JSON.parse(out.trim());
  } catch (e) {
    if (e.message && e.message.includes('ENOENT')) return null;
    throw e;
  }
}

// Helper: build a minimal markdown question block
function buildMd({ grade = 'G3', num = 1, difficulty = 'Easy', title = 'Test', en = 'What is 2+2?', fr = 'Combien fait 2+2?', choices = 'A) 3  B) 4  C) 5  D) 6', answer = '4' }) {
  return `# Daily Math - 2026-01-01

## ${grade}
${num}. **[${difficulty}] ${title}**
   - EN: ${en}
   - FR: ${fr}
   - Choices: ${choices}
   - Hint: Think carefully.
   - Steps:
     - step 1
     - step 2
   - Answer: ${answer}

## Today's Encouragement
Keep it up!
`;
}

describe('Quiz answer validation', () => {
  // Check if Python is available
  let pythonAvailable = true;
  beforeAll(() => {
    try {
      execSync('python --version', { encoding: 'utf-8' });
    } catch {
      pythonAvailable = false;
    }
  });

  function skipIfNoPython() {
    if (!pythonAvailable) return true;
    return false;
  }

  describe('Stripped fractions (e.g. 14 instead of 1/4)', () => {
    it('flags answer "14" when choices contain "1/4"', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'A pizza is cut into 4 equal slices. Emma eats 1. What fraction?',
        choices: 'A) 1/2  B) 1/3  C) 2/4  D) 1/4',
        answer: '14',
      });
      const issues = validateMd(md);
      expect(issues.length).toBeGreaterThan(0);
      const err = issues.find(i => i.level === 'error');
      expect(err).toBeDefined();
      expect(err.msg).toMatch(/stripped/i);
      expect(err.fix).toBe('1/4');
    });

    it('flags answer "12" when choices contain "1/2"', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'Which is bigger: 1/2 or 1/4?',
        choices: 'A) 1/4  B) They are equal  C) 1/2  D) Cannot tell',
        answer: '12',
      });
      const issues = validateMd(md);
      const err = issues.find(i => i.level === 'error');
      expect(err).toBeDefined();
      expect(err.fix).toBe('1/2');
    });

    it('flags answer "34" when choices contain "3/4"', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'What fraction is shaded?',
        choices: 'A) 1/4  B) 1/2  C) 3/4  D) 2/3',
        answer: '34',
      });
      const issues = validateMd(md);
      const err = issues.find(i => i.level === 'error');
      expect(err).toBeDefined();
      expect(err.fix).toBe('3/4');
    });
  });

  describe('Stripped currency (e.g. 30 instead of $30)', () => {
    it('flags answer "30" when choices contain "$30"', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'How much does it cost?',
        choices: 'A) $20  B) $30  C) $40  D) $50',
        answer: '30',
      });
      const issues = validateMd(md);
      const err = issues.find(i => i.level === 'error');
      expect(err).toBeDefined();
      expect(err.fix).toBe('$30');
    });

    it('flags answer "675" when choices contain "$6.75"', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'What is the total cost?',
        choices: 'A) $5.75  B) $6.75  C) $7.25  D) $6.25',
        answer: '675',
      });
      const issues = validateMd(md);
      const err = issues.find(i => i.level === 'error');
      expect(err).toBeDefined();
      expect(err.fix).toBe('$6.75');
    });
  });

  describe('Stripped time (e.g. 1230 instead of 12:30)', () => {
    it('flags answer "1230" when choices contain "12:30"', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'What time is half past 12?',
        choices: 'A) 12:00  B) 12:15  C) 1:00  D) 12:30',
        answer: '1230',
      });
      const issues = validateMd(md);
      const err = issues.find(i => i.level === 'error');
      expect(err).toBeDefined();
      expect(err.fix).toBe('12:30');
    });
  });

  describe('Stripped decimals (e.g. 03 instead of 0.3)', () => {
    it('flags answer "03" when choices contain "0.3"', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'What is 3 tenths as a decimal?',
        choices: 'A) 3  B) 0.03  C) 0.3  D) 30',
        answer: '03',
      });
      const issues = validateMd(md);
      const err = issues.find(i => i.level === 'error');
      expect(err).toBeDefined();
      expect(err.fix).toBe('0.3');
    });
  });

  describe('Answer matches no choice at all', () => {
    it('flags answer "99" that does not match any choice', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'What is 5 + 3?',
        choices: 'A) 7  B) 8  C) 9  D) 6',
        answer: '99',
      });
      const issues = validateMd(md);
      const err = issues.find(i => i.level === 'error');
      expect(err).toBeDefined();
      expect(err.msg).toMatch(/does not match any choice/);
    });
  });

  describe('Correct answers pass validation', () => {
    it('no issues for correct integer answer', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'What is 2 + 2?',
        choices: 'A) 3  B) 4  C) 5  D) 6',
        answer: '4',
      });
      const issues = validateMd(md);
      expect(issues.length).toBe(0);
    });

    it('no issues for correct fraction answer', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'What fraction is 1 out of 4?',
        choices: 'A) 1/2  B) 1/3  C) 1/4  D) 2/4',
        answer: '1/4',
      });
      const issues = validateMd(md);
      expect(issues.length).toBe(0);
    });

    it('no issues for correct currency answer', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'What is the total?',
        choices: 'A) $10  B) $20  C) $30  D) $40',
        answer: '$20',
      });
      const issues = validateMd(md);
      expect(issues.length).toBe(0);
    });

    it('no issues for correct time answer', () => {
      if (skipIfNoPython()) return;
      const md = buildMd({
        en: 'What time?',
        choices: 'A) 3:00  B) 3:30  C) 4:00  D) 4:30',
        answer: '3:30',
      });
      const issues = validateMd(md);
      expect(issues.length).toBe(0);
    });
  });
});
