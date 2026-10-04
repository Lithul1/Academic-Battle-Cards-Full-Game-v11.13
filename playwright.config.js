// Playwright: real-browser tests for things jsdom cannot see -- layout,
// dragging a slider, what the browser actually keeps or replaces.
//   npm run test:e2e          (builds dist/stub.html first, then runs tests/e2e)
// One-time setup: npx playwright install chromium
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: 'tests/e2e',
  globalSetup: require.resolve('./tests/e2e/build-stub.js'),
  fullyParallel: true,
  reporter: [['list']],
  use: {
    // the game is one self-contained file: no server needed
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
