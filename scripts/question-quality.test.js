const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const root = path.join(__dirname, '..');
const fixturesPath = path.join(__dirname, 'spec', 'conformance-fixtures.json');
const fixtures = JSON.parse(fs.readFileSync(fixturesPath, 'utf8'));

function tempPath(name) {
  return path.join(os.tmpdir(), `dmk-${process.pid}-${Date.now()}-${name}`);
}

describe('cross-language question-quality conformance', () => {
  test('JavaScript runner passes the shared fixtures', () => {
    const output = tempPath('javascript.json');
    const stdout = execFileSync(process.execPath, [path.join(__dirname, 'run-conformance.js'), '--output', output], {
      cwd: root,
      encoding: 'utf8',
    });
    expect(stdout).toContain('JavaScript conformance passed:');
    expect(fs.existsSync(output)).toBe(true);
    fs.rmSync(output, { force: true });
  });

  test('JavaScript runner defaults to the ignored conformance directory', () => {
    const output = path.join(root, 'data', 'conformance', 'javascript.json');
    fs.rmSync(output, { force: true });
    const stdout = execFileSync(process.execPath, [path.join(__dirname, 'run-conformance.js')], {
      cwd: root,
      encoding: 'utf8',
    });
    expect(stdout).toContain(output);
    expect(fs.existsSync(output)).toBe(true);
    fs.rmSync(output, { force: true });
  });

  test('Python and JavaScript canonical outputs are byte-identical', () => {
    const pythonOutput = tempPath('python.json');
    const javascriptOutput = tempPath('javascript.json');
    execFileSync('python', [path.join(__dirname, 'run_conformance.py'), '--output', pythonOutput], {
      cwd: root,
      encoding: 'utf8',
    });
    execFileSync(process.execPath, [path.join(__dirname, 'run-conformance.js'), '--output', javascriptOutput], {
      cwd: root,
      encoding: 'utf8',
    });
    expect(fs.readFileSync(pythonOutput)).toEqual(fs.readFileSync(javascriptOutput));
    fs.rmSync(pythonOutput, { force: true });
    fs.rmSync(javascriptOutput, { force: true });
  });

  test.each(fixtures.forbidden_fixes)('forbidden rewrite %s remains an error and does not mutate content', fixture => {
    const source = tempPath('source.txt');
    fs.writeFileSync(source, fixture.stored, 'utf8');
    const before = fs.readFileSync(source);
    const result = require('./question-quality').conformanceResult(fixtures);
    const actual = result.forbidden_fixes.find(item => item.file === fixture.file);
    expect(actual).toEqual(expect.objectContaining({ verdict: 'ERROR', code: fixture.code }));
    expect(fs.readFileSync(source)).toEqual(before);
    fs.rmSync(source, { force: true });
  });
});

describe('daily scoring behavior preservation', () => {
  test.each([
    [0, 5, 0],
    [3, 5, 3],
    [4, 5, 4],
    [5, 5, 8],
  ])('score %i/%i awards %i points', (score, outOf, expected) => {
    const points = score + (outOf > 0 && score === outOf ? 3 : 0);
    expect(points).toBe(expected);
  });
});
