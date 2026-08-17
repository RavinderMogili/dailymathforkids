const fs = require('fs');
const path = require('path');
const engine = require('./practice-engine.js');
const quality = require('./question-quality.js');

function seeded(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

describe('practice engine safety seams', () => {
  afterEach(() => engine.resetRandomSource());

  test('seeded generation is reproducible', () => {
    engine.setRandomSource(seeded(1168085));
    const first = engine.generateQuestion(5, 'Percentages', 'easy');
    engine.setRandomSource(seeded(1168085));
    const second = engine.generateQuestion(5, 'Percentages', 'easy');
    expect(second).toEqual(first);
  });

  test('makeChoices fails explicitly when distractor space is insufficient', () => {
    expect(() => engine.makeChoices('5%', 4, () => '5%')).toThrow('INSUFFICIENT_DISTRACTOR_SPACE');
  });

  test('choices are canonical, distinct, and contain exactly one answer', () => {
    engine.setRandomSource(seeded(3071280));
    const q = engine.generateQuestion(6, 'Percent & Discount', 'hard');
    expect(q.choices).toHaveLength(4);
    expect(new Set(q.choices).size).toBe(4);
    expect(q.choices.filter(choice => quality.equivalentStrings(choice, q.answer)[0])).toHaveLength(1);
    expect(q.choices.every(choice => choice !== undefined && choice !== null && choice !== 'NaN')).toBe(true);
  });

  test.each([
    [5, 'Coordinate Plane'],
    [7, 'Operations with Rationals'],
    [8, 'Transformations'],
    [10, 'Circle Geometry'],
    [10, 'Coordinate Geometry'],
    [11, 'Functions'],
    [12, 'Proof & Logic'],
  ])('unsupported topic %s is hidden and hard-fails', (grade, topic) => {
    expect(engine.getTopicsForGrade(grade)).not.toContain(topic);
    expect(() => engine.generateQuestion(grade, topic, 'easy')).toThrow('UNSUPPORTED_TOPIC');
  });

  test('grade-specific unsupported topics do not hide the Grade 8 Functions topic', () => {
    expect(engine.getTopicsForGrade(8)).toContain('Functions');
    expect(() => engine.generateQuestion(8, 'Functions', 'easy')).not.toThrow();
  });

  test('unknown topics do not silently fall back', () => {
    expect(() => engine.generateQuestion(3, 'Not a topic', 'easy')).toThrow('UNSUPPORTED_TOPIC');
  });

  test('pool schema and reachability are explicit', () => {
    const pool = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'practice-pool.json'), 'utf8'));
    expect(() => engine.validatePracticePool(pool)).not.toThrow();
    expect(pool).toHaveLength(60);
    for (const item of pool) {
      const uiTopics = engine.POOL_TOPIC_MAP[item.topic];
      expect(uiTopics.some(topic => engine.getTopicsForGrade(item.grade).includes(topic))).toBe(true);
    }
  });

  test('affected generators terminate across seeded regression cases', () => {
    const cases = [
      [5, 'Percentages'], [6, 'Statistics'], [9, 'Data Analysis'],
      [1, 'Comparing Numbers'], [6, 'Percent & Discount'], [3, 'Fractions'],
      [1, 'Geometry'], [4, 'Factors & Multiples'], [4, 'Multi-digit Arithmetic'],
      [8, 'Linear Equations'],
    ];
    const seeds = [1168085, 1191905, 1296570, 1344084, 1344127, 1344140, 3071280, 3071282, 3280738, 3280757, 5087125, 6352020];
    for (const [grade, topic] of cases) {
      for (const difficulty of ['easy', 'medium', 'hard']) {
        for (const seed of seeds) {
          engine.setRandomSource(seeded(seed));
          const q = engine.generateQuestion(grade, topic, difficulty);
          expect(q.choices).toHaveLength(4);
          expect(new Set(q.choices).size).toBe(4);
          expect(q.choices.some(choice => quality.equivalentStrings(choice, q.answer)[0])).toBe(true);
        }
      }
    }
  });

  test('all supported topic combinations satisfy the bounded choice property', () => {
    for (const grade of Object.keys(engine.TOPICS_BY_GRADE).map(Number)) {
      for (const topic of engine.TOPICS_BY_GRADE[grade]) {
        if (topic === 'Word Problems' || (grade === 11 && topic === 'Functions')) continue;
        for (const difficulty of ['easy', 'medium', 'hard']) {
          for (let index = 0; index < 2000; index++) {
            engine.setRandomSource(seeded((grade * 100000 + topic.length * 1000 + difficulty.length * 100 + index) >>> 0));
            const question = engine.generateQuestion(grade, topic, difficulty);
            expect(question.choices).toHaveLength(4);
            expect(new Set(question.choices).size).toBe(4);
            expect(question.choices.filter(choice => quality.equivalentStrings(choice, question.answer)[0])).toHaveLength(1);
            expect(question.choices.every(choice => choice !== undefined && choice !== null && !['NaN', 'undefined', 'null'].includes(String(choice)))).toBe(true);
          }
        }
      }
    }
  }, 120000);
});
