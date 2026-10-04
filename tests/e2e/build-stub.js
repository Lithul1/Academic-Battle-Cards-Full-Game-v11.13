// Playwright globalSetup: build dist/stub.html from src (1x1 images, no
// assets.json needed) so the browser tests always run against current code.
const { execFileSync } = require('child_process');
const path = require('path');

module.exports = async () => {
  const root = path.join(__dirname, '..', '..');
  // python3 on macOS/Linux, python on Windows -- where "python3" may be the
  // Microsoft Store placeholder, which fails rather than being missing
  let last;
  for (const py of ['python3', 'python']) {
    try {
      execFileSync(py, ['build.py', '--stub'], { cwd: root, stdio: 'pipe' });
      return;
    } catch (e) { last = e; }
  }
  throw new Error(`could not build dist/stub.html (needs Python 3):\n${(last.stderr || last.message).toString()}`);
};
