/**
 * Jest unit tests for the Math Helper topic detector.
 * Run with: npm run test:unit
 */

const fs = require('fs');
const path = require('path');

// Load math-helper.js into the jsdom environment before tests
const helperPath = path.join(__dirname, 'math-helper.js');
const helperCode = fs.readFileSync(helperPath, 'utf8');

beforeAll(() => {
  // math-helper.js is an IIFE that registers window.openMathHelper and window.__mh_detectTopic
  eval(helperCode);
});

const cases = {
  volume: [
    'A box is 5 cm long, 3 cm wide, and 2 cm high. How much can it hold?',
    'Find the volume of a cube with side length 4 cm.',
    'A tank can hold 50 liters of water. How many milliliters is that?',
    'What is the capacity of a container that measures 10 cm by 6 cm by 4 cm?',
    'A cuboid has length 8, width 3, and height 2. Find its volume.',
    'How many cups will fill a gallon jug?',
    'A tank holds 100 liters. 30 liters are removed. How much is left?',
    'A box has 12 cubes. 5 are taken out. How many remain?',
  ],
  mass: [
    'A bag of apples weighs 2 kg. How many grams is that?',
    'Which is heavier, 500 g or 1 kg?',
    'A puppy weighs 4 pounds. Convert to ounces.',
    'Find the mass of an object that weighs 250 g.',
    'The box is lighter than the crate. What is the difference in weight?',
  ],
  geometry: [
    'Find the area of a rectangle with length 7 and width 4.',
    'What is the perimeter of a square with side 9?',
    'A triangle has a base of 6 and height of 3. Find its area.',
    'Calculate the circumference of a circle with radius 5.',
    'A polygon has 5 sides. What is it called?',
  ],
  fractions: [
    'What is 3/4 of 12?',
    'Shade half of the circle.',
    'A pizza is cut into 8 slices. If you eat 3, what fraction did you eat?',
    'What is the numerator of 5/6?',
  ],
  percentage: [
    'What is 20% of 80?',
    'A shirt costs $40 and is 25% off. What is the discount?',
    'Find the percentage of students who chose red.',
  ],
  multiplication: [
    'There are 4 boxes with 6 crayons each. How many crayons in total?',
    '3 times 7 equals what?',
    'A garden has 5 rows of 8 plants. How many plants?',
    'Find the product of 6 and 9.',
  ],
  division: [
    'Share 24 cookies equally among 6 friends.',
    'What is 56 divided by 8?',
    'A teacher splits 30 students into groups of 5. How many groups?',
    'Find the quotient of 45 and 9.',
  ],
  subtraction: [
    'There are 15 birds on a tree. 6 fly away. How many are left?',
    'What is the difference between 83 and 57?',
    'You had 50 stickers and gave away 18. How many remain?',
    'How many more apples does Sam have than Jill?',
  ],
  addition: [
    'Mia has 12 marbles and gets 8 more. How many in total?',
    'Find the sum of 45 and 37.',
    'There are 5 red balls and 7 blue balls. How many altogether?',
  ],
  patterns: [
    'What comes next in the pattern: 2, 5, 8, 11, ...?',
    'Find the rule for the sequence 4, 8, 12, 16.',
  ],
  time: [
    'A movie starts at 2:30 PM and ends at 4:15 PM. How long is it?',
    'What time is it 45 minutes after 9:10?',
    'The bus leaves at 8:00 AM and arrives at 10:30 AM. How long is the trip?',
  ],
  money: [
    'A toy costs $12.50. You pay with $20. How much change?',
    'What is the total cost of 3 notebooks at $2 each?',
    'You have 3 loonies and 2 toonies. How much money?',
  ],
  algebra: [
    'Solve for x: x + 5 = 12.',
    'If 3y = 18, what is y?',
    'Find the value of the expression 2a + 3 when a = 4.',
  ],
  statistics: [
    'Find the mean of 4, 7, 9, 12.',
    'What is the median of these scores?',
    'What is the probability of rolling a 3 on a die?',
  ],
  general: [
    'What is the next number in this list?',
    'Explain your answer.',
  ],
};

describe('Math Helper topic detection', () => {
  Object.entries(cases).forEach(([topic, questions]) => {
    describe(`detects ${topic}`, () => {
      questions.forEach((q) => {
        test(`"${q}"`, () => {
          expect(window.__mh_detectTopic(q)).toBe(topic);
        });
      });
    });
  });
});
