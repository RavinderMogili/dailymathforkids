const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const scripts = __dirname;

function validateMd(md, allowNonvalid = 0) {
  const runnerPath = path.join(os.tmpdir(), `_validate_quiz_runner_${process.pid}.py`);
  const quizPath = path.join(os.tmpdir(), `_validate_quiz_${process.pid}.md`);
  const runner = `
import json, pathlib, sys
sys.path.insert(0, r'${scripts.replace(/\\/g, '\\\\')}')
from validate_quiz import validate_run
path = pathlib.Path(r'${quizPath.replace(/\\/g, '\\\\')}')
path.write_text(sys.stdin.read(), encoding='utf-8')
print(json.dumps(validate_run(path, '2026-01-01', allow_nonvalid=${allowNonvalid})))
`;
  fs.writeFileSync(runnerPath, runner, 'utf8');
  try {
    return JSON.parse(execFileSync('python', [runnerPath], { input: md, encoding: 'utf8' }));
  } finally {
    fs.rmSync(runnerPath, { force: true });
    fs.rmSync(quizPath, { force: true });
  }
}

function question() {
  return `# Daily Math - fixture

## G3
1. **[Easy] Addition**
   - EN: 2 + 2 = ?
   - FR: 2 + 2 = ?
   - Choices: A) 4  B) 3  C) 5  D) 6
   - Hint: Add two different numbers.
   - Steps:
     - 1 + 1 = 2.
   - Answer: 4
`;
}

describe('fail-closed quiz validation', () => {
  test('valid deterministic question has no question-level errors', () => {
    const result = validateMd(question());
    const item = result.questions.find(entry => entry.grade === 'G3');
    expect(item.verdict).toBe('VALID');
    expect(item.codes).toEqual([]);
  });

  test('no correct option blocks publication', () => {
    const result = validateMd(question().replace('Answer: 4', 'Answer: 9'));
    expect(result.publication_allowed).toBe(false);
    expect(result.issues.some(item => item.code === 'NO_CORRECT_OPTION')).toBe(true);
  });

  test('duplicate choices block publication', () => {
    const result = validateMd(question().replace('A) 4  B) 3', 'A) 4  B) 4'));
    expect(result.publication_allowed).toBe(false);
    expect(result.issues.some(item => item.code === 'DUPLICATE_CHOICES')).toBe(true);
  });

  test('missing French blocks markdown publication', () => {
    const result = validateMd(question().replace('   - FR: 2 + 2 = ?\n', ''));
    expect(result.publication_allowed).toBe(false);
    expect(result.issues.some(item => item.code === 'MISSING_FIELD')).toBe(true);
  });

  test('unsupported question is non-valid and allowance remains fail-closed by default', () => {
    const unsupported = question().replace('2 + 2 = ?', 'Explain why numbers exist.');
    const result = validateMd(unsupported);
    expect(result.publication_allowed).toBe(false);
    expect(result.issues.some(item => item.code === 'UNVERIFIED')).toBe(true);
  });

  test('validator reports errors without a fix or content mutation', () => {
    const source = question().replace('Answer: 4', 'Answer: 44');
    const result = validateMd(source);
    expect(result.publication_allowed).toBe(false);
    expect(result.issues.some(item => item.code === 'NO_CORRECT_OPTION')).toBe(true);
    expect(source).toBe(question().replace('Answer: 4', 'Answer: 44'));
  });
});
