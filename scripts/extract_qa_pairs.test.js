/**
 * Regression tests for extract_qa_pairs in gen_site.py.
 *
 * Bug history (2026-07-05): the old extraction used two independent regex
 * scans for '- EN:' and '- Answer:' lines. When the LLM wrote an extra
 * '- Answer:' line inside the Steps list, the answers array gained extra
 * entries and shifted — students were graded against the wrong answers and
 * Mistake History showed mismatched question/answer pairs.
 *
 * Run with: npm run test:unit
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Helper: run extract_qa_pairs via a Python subprocess on inline markdown
function extractPairs(md) {
  const runnerPath = path.join(os.tmpdir(), '_extract_qa_pairs_runner.py');
  const runner = `
import sys, json
sys.path.insert(0, r'${path.join(__dirname).replace(/\\/g, '\\\\')}')
from gen_site import parse_grade_sections, extract_qa_pairs
text = sys.stdin.read()
sections = parse_grade_sections(text)
result = {}
for code, content in sections.items():
    qs, ans = extract_qa_pairs(content)
    result[code] = {'questions': qs, 'answers': ans}
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

describe('extract_qa_pairs (quiz question/answer alignment)', () => {
  let pythonAvailable = true;
  beforeAll(() => {
    try {
      execSync('python --version', { encoding: 'utf-8' });
    } catch {
      pythonAvailable = false;
    }
  });

  function skipIfNoPython() {
    return !pythonAvailable;
  }

  it('extracts aligned pairs from a normal quiz', () => {
    if (skipIfNoPython()) return;
    const md = `# Daily Math - 2026-01-01

## G4
1. **[Easy] Multiplication**
   - EN: What is 7 x 8?
   - FR: Combien font 7 x 8?
   - Choices: A) 54  B) 56  C) 58  D) 60
   - Hint: Think of 7 x 8.
   - Steps:
     - 7 x 8 = 56.
   - Answer: 56

2. **[Easy] Addition**
   - EN: What is 10 + 5?
   - FR: Combien font 10 + 5?
   - Choices: A) 14  B) 15  C) 16  D) 17
   - Hint: Add them.
   - Steps:
     - 10 + 5 = 15.
   - Answer: 15
`;
    const result = extractPairs(md);
    if (!result) return;
    expect(result.G4.questions).toEqual(['What is 7 x 8?', 'What is 10 + 5?']);
    expect(result.G4.answers).toEqual(['56', '15']);
  });

  it('REGRESSION 2026-07-05: extra "- Answer:" line inside Steps does not shift following answers', () => {
    if (skipIfNoPython()) return;
    const md = `# Daily Math - 2026-07-05

## G4
1. **[Medium] Decimal Operations**
   - EN: What is 2.5 + 1.3?
   - FR: Combien font 2,5 + 1,3?
   - Choices: A) 3.5  B) 3.7  C) 3.8  D) 4.0
   - Hint: Line up the decimal points.
   - Steps:
     - Ones: 2 + 1 = 3.
     - Tenths: 5 + 3 = 8.
     - Answer: 3.8
   - Answer: 3.8

2. **[Medium] Multi-Step Multiplication**
   - EN: A hockey team has 6 players on ice. If 9 teams are playing, how many players are on ice in total?
   - FR: Une equipe de hockey a 6 joueurs sur la glace.
   - Choices: A) 48  B) 54  C) 60  D) 63
   - Hint: Multiply players by teams.
   - Steps:
     - 6 x 9 = 54.
   - Answer: 54

3. **[Medium] Division**
   - EN: What is 138 / 6?
   - FR: Combien font 138 / 6?
   - Choices: A) 21  B) 22  C) 23  D) 24
   - Hint: Divide step by step.
   - Steps:
     - 138 / 6 = 23.
     - Answer: 23
   - Answer: 23
`;
    const result = extractPairs(md);
    if (!result) return;
    // 3 questions must produce exactly 3 answers — not 5
    expect(result.G4.questions).toHaveLength(3);
    expect(result.G4.answers).toHaveLength(3);
    // Each question paired with ITS answer (the bug paired hockey with 3.8)
    expect(result.G4.answers).toEqual(['3.8', '54', '23']);
    expect(result.G4.questions[1]).toContain('hockey');
    expect(result.G4.answers[1]).toBe('54');
  });

  it('keeps a placeholder for a question with no Answer line so numbering stays aligned', () => {
    if (skipIfNoPython()) return;
    const md = `# Daily Math - 2026-01-01

## G10
1. **[Easy] Squares**
   - EN: What is 3 squared?
   - FR: Combien font 3 au carre?
   - Choices: A) 6  B) 9  C) 12  D) 27
   - Hint: Multiply 3 by itself.
   - Answer: 9

2. **[Medium] Truncated question**
   - EN: What is the maximum value of the function f(x) = -x
   - FR: Question tronquee.
   - Choices: A) 0  B) 1  C) 2  D) 3

3. **[Easy] Roots**
   - EN: What is the square root of 49?
   - FR: Quelle est la racine carree de 49?
   - Choices: A) 6  B) 7  C) 8  D) 9
   - Answer: 7
`;
    const result = extractPairs(md);
    if (!result) return;
    expect(result.G10.questions).toHaveLength(3);
    expect(result.G10.answers).toHaveLength(3);
    // Question 2 has no answer -> empty placeholder, question 3 stays paired
    expect(result.G10.answers).toEqual(['9', '', '7']);
  });

  it('handles multiple grades independently', () => {
    if (skipIfNoPython()) return;
    const md = `# Daily Math - 2026-01-01

## G1
1. **[Easy] Counting**
   - EN: What is 1 + 1?
   - FR: Combien font 1 + 1?
   - Choices: A) 1  B) 2  C) 3  D) 4
   - Answer: 2

## G2
1. **[Easy] Addition**
   - EN: What is 5 + 5?
   - FR: Combien font 5 + 5?
   - Choices: A) 9  B) 10  C) 11  D) 12
   - Steps:
     - Answer: 10
   - Answer: 10
`;
    const result = extractPairs(md);
    if (!result) return;
    expect(result.G1.questions).toEqual(['What is 1 + 1?']);
    expect(result.G1.answers).toEqual(['2']);
    expect(result.G2.questions).toEqual(['What is 5 + 5?']);
    expect(result.G2.answers).toEqual(['10']);
  });
});
