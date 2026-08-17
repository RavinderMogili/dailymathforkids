'use strict';

const fs = require('fs');
const path = require('path');
const {
  conformanceResult,
} = require('./question-quality');

const root = path.resolve(__dirname, '..');
const fixturesPath = path.join(root, 'scripts', 'spec', 'conformance-fixtures.json');
const outputIndex = process.argv.indexOf('--output');

const fixtures = JSON.parse(fs.readFileSync(fixturesPath, 'utf8'));
const result = conformanceResult(fixtures);
const fail = message => { throw new Error(message); };

fixtures.parse.forEach((item, index) => {
  const actual = result.parse[index].result;
  if (item.expect === 'PARSE_FAILED') {
    if (actual.status !== 'PARSE_FAILED' || actual.code !== item.code) fail(`parse fixture failed: ${item.input}`);
  } else if (JSON.stringify(actual) !== JSON.stringify(item.expect)) {
    fail(`parse fixture failed: ${item.input}: ${JSON.stringify(actual)}`);
  }
});
fixtures.equivalence.forEach((item, index) => {
  const actual = result.equivalence[index];
  if (actual.equal !== item.equal || (!item.equal && actual.code !== item.code)) fail(`equivalence fixture failed: ${item.a} / ${item.b}`);
});
fixtures.forbidden_fixes.forEach((item, index) => {
  const actual = result.forbidden_fixes[index];
  if (actual.verdict !== 'ERROR' || actual.code !== item.code) fail(`forbidden fixer fixture failed: ${item.file}`);
});
fixtures.questions.forEach((item, index) => {
  const actual = result.questions[index];
  if (actual.verdict !== item.expect.verdict || JSON.stringify(actual.codes) !== JSON.stringify(item.expect.codes)) fail(`question fixture failed: ${item.id}`);
});
fixtures.bounded_termination.forEach((item, index) => {
  const actual = result.bounded_termination[index];
  if (actual.code !== item.expect.code || !actual.must_terminate) fail(`termination fixture failed: ${item.id}`);
});

function sortKeys(value) {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === 'object') {
    return Object.keys(value).sort().reduce((out, key) => {
      out[key] = sortKeys(value[key]);
      return out;
    }, {});
  }
  return value;
}

const output = JSON.stringify(sortKeys(result), null, 0);
const outputPath = outputIndex >= 0 && process.argv[outputIndex + 1]
  ? process.argv[outputIndex + 1]
  : path.join(root, 'data', 'conformance', 'javascript.json');
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, `${output}\n`, 'utf8');
console.log(`JavaScript conformance passed: ${outputPath}`);
