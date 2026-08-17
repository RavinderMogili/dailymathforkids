module.exports = {
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/scripts'],
  testMatch: ['**/*.test.js'],
  collectCoverage: false,
  setupFilesAfterEnv: ['<rootDir>/scripts/jest-offline-setup.js'],
};
