// Changing a setting updates that setting in place -- it must not redraw the
// screen. A redraw replaced every element, including the slider being dragged.
//
// "Not redrawn" is checked directly: we hold on to real DOM nodes (the board,
// the settings panel, the control itself) and assert they are still the same
// nodes, still attached, after the change.
const { test, expect } = require('@playwright/test');
const path = require('path');
const { pathToFileURL } = require('url');

const STUB = pathToFileURL(path.join(__dirname, '..', '..', 'dist', 'stub.html')).href;

const settings = page => page.evaluate(() => window.ABC_DEBUG.S.settings);
const attached = (...handles) => Promise.all(handles.map(h => h.evaluate(n => n.isConnected)));
const row = (page, label) => page.locator('label.set-row', { hasText: label });

// Wait until the game has stopped redrawing on its own. Dealing the opening
// hand redraws the whole screen a dozen times over ~3s -- legitimately -- and
// a test that grabs nodes during that would blame the settings for it.
async function settle(page, quietMs = 700) {
  await page.evaluate(quiet => new Promise(done => {
    const game = document.getElementById('game');
    let timer = setTimeout(finish, quiet);
    const mo = new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(finish, quiet); });
    mo.observe(game, { childList: true });
    function finish() { mo.disconnect(); done(); }
  }), quietMs);
}

// Quickplay -> Normal -> the in-game Tune panel, with the AI held off
async function openInGameTune(page) {
  await page.goto(STUB);
  await page.getByText('Quickplay', { exact: true }).click();
  await page.getByText('Honor Roll', { exact: true }).click();
  await page.waitForFunction(() => window.ABC_DEBUG && window.ABC_DEBUG.S && window.ABC_DEBUG.S.phase === 'draw');
  await page.evaluate(() => { window.ABC_DEBUG.noAI = true; });
  await settle(page);
  await page.getByRole('button', { name: /Tune/ }).click();
  await expect(page.locator('.settings .set-title')).toBeVisible();
}

// drag a range input's thumb from its left end to `frac` of the way across,
// in several steps, the way a player does
async function drag(page, slider, frac) {
  await slider.scrollIntoViewIfNeeded();
  const box = await slider.boundingBox();
  const y = box.y + box.height / 2;
  await page.mouse.move(box.x + 2, y);
  await page.mouse.down();
  for (let i = 1; i <= 8; i++) await page.mouse.move(box.x + 2 + (box.width - 4) * frac * i / 8, y);
  await page.mouse.up();
}

test.describe('in-game Tune panel', () => {
  test.beforeEach(async ({ page }) => { await openInGameTune(page); });

  test('dragging the turn timer slider keeps the same slider and only updates its label', async ({ page }) => {
    const slider = row(page, 'Turn timer').locator('input[type=range]');
    const [sliderEl, panel, board, topbar] = await Promise.all([
      slider.elementHandle(), page.locator('.settings').elementHandle(),
      page.locator('.board').elementHandle(), page.locator('.topbar').elementHandle()]);
    const before = (await settings(page)).turnTimer;

    await drag(page, slider, 0.1);                       // drag toward the 10s end

    const after = (await settings(page)).turnTimer;
    expect(after).not.toBe(before);
    expect(after).toBeLessThan(before);
    await expect(row(page, 'Turn timer').locator('span').first()).toHaveText(`Turn timer: ${after}s`);
    expect(await attached(sliderEl, panel, board, topbar)).toEqual([true, true, true, true]);
    expect(await sliderEl.evaluate(n => n.value)).toBe(String(after));
  });

  test('a checkbox flips its setting without redrawing anything', async ({ page }) => {
    const box = row(page, 'Auto-block').locator('input[type=checkbox]');
    const [boxEl, panel, board] = await Promise.all([
      box.elementHandle(), page.locator('.settings').elementHandle(), page.locator('.board').elementHandle()]);
    const before = (await settings(page)).autoBlock;
    await box.click();
    expect((await settings(page)).autoBlock).toBe(!before);
    expect(await attached(boxEl, panel, board)).toEqual([true, true, true]);
    await expect(box).toBeChecked({ checked: !before });
  });

  test('Timer position moves only the turn bar', async ({ page }) => {
    const [panel, board] = await Promise.all([
      page.locator('.settings').elementHandle(), page.locator('.board').elementHandle()]);
    await expect(page.locator('.midline #turnclock')).toHaveCount(1);

    await row(page, 'Timer position').locator('select').selectOption('topright');

    expect((await settings(page)).timerPos).toBe('topright');
    await expect(page.locator('.turnbar-float.pos-topright #turnclock')).toHaveCount(1);
    await expect(page.locator('#turnclock')).toHaveCount(1);
    expect(await attached(panel, board)).toEqual([true, true]);

    await row(page, 'Timer position').locator('select').selectOption('middle');
    await expect(page.locator('.midline #turnclock')).toHaveCount(1);
    await expect(page.locator('.turnbar-float')).toHaveCount(0);
    expect(await attached(panel, board)).toEqual([true, true]);
  });

  test('KOs needed to win updates the score chips in place', async ({ page }) => {
    const slider = row(page, 'KOs needed').locator('input[type=range]');
    const [panel, board] = await Promise.all([
      page.locator('.settings').elementHandle(), page.locator('.board').elementHandle()]);
    await slider.fill('5');
    expect((await settings(page)).koTarget).toBe(5);
    await expect(row(page, 'KOs needed').locator('span').first()).toHaveText('KOs needed to win: 5');
    await expect(page.locator('.score .kos.you')).toHaveText(/\/5$/);
    await expect(page.locator('.score .kos.opp')).toHaveText(/\/5$/);
    expect(await attached(panel, board)).toEqual([true, true]);
  });

  test('audio: volume relabels and the track highlight moves, in place', async ({ page }) => {
    const vol = row(page, 'Music volume').locator('input[type=range]');
    const panel = await page.locator('.settings').elementHandle();
    await vol.fill('35');
    await expect(row(page, 'Music volume').locator('span').first()).toHaveText('Music volume: 35%');

    const hop = page.locator('.trk-opt[data-audio="track:hoplofi"]');
    const hopEl = await hop.elementHandle();
    await hop.click();
    await expect(hop).toHaveClass(/\bon\b/);
    await expect(page.locator('.trk-opt.on')).toHaveCount(1);
    expect(await attached(panel, hopEl)).toEqual([true, true]);
  });
});

test('pre-game House Rules: sliders update in place there too', async ({ page }) => {
  await page.goto(STUB);
  await page.getByText('Custom Play', { exact: true }).click();
  await page.getByText('Honor Roll', { exact: true }).click();
  await page.getByRole('button', { name: /Set house rules/ }).click();
  await settle(page);
  const slider = row(page, 'Bench size').locator('input[type=range]');
  const [sliderEl, panel] = await Promise.all([
    slider.elementHandle(), page.locator('.tune-panel').elementHandle()]);

  await drag(page, slider, 1);                            // all the way to the max

  const bench = await page.evaluate(() => window.ABC_DEBUG.APP.settings.benchSize);
  expect(bench).toBe(4);
  await expect(row(page, 'Bench size').locator('span').first()).toHaveText('Bench size: 4');
  expect(await attached(sliderEl, panel)).toEqual([true, true]);
});
