import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../../../prototypes/dragon-tide/index.html", import.meta.url), "utf8");
const profileFixture = JSON.parse(readFileSync(new URL("./fixtures/profile-v3.68.0.json", import.meta.url), "utf8"));
const runFixture = JSON.parse(readFileSync(new URL("./fixtures/run-v3.68.0.json", import.meta.url), "utf8"));
const profileKey = "dragonTide_profile";
const runKey = "dragonTide_run";

// Top-level declarations end at an unindented brace in this single-file prototype.
// Fail explicitly if its structure changes, rather than silently testing copied implementations.
function extractFunction(name) {
  const match = source.match(new RegExp(`^function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?^\\}`, "m"));
  assert.ok(match, `Could not extract game function ${name}`);
  return match[0];
}

function extractConstant(name) {
  const match = source.match(new RegExp(`^const ${name}\\s*=\\s*[^\\n]+?;`, "m"));
  assert.ok(match, `Could not extract game constant ${name}`);
  return match[0];
}

function createStorageRuntime(entries = {}) {
  const values = new Map(Object.entries(entries));
  const context = vm.createContext({
    // Only the migration's bounds are stubbed; loading and migration code are production functions.
    CONTINENT_DEFS: Array.from({ length: 8 }, () => ({})),
    localStorage: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, String(value)),
      removeItem: (key) => values.delete(key),
    },
  });
  const constants = ["BEST_TIME_KEY", "BEST_KILLS_KEY", "PROFILE_KEY", "RUN_SAVE_KEY", "PROFILE_VERSION", "RUN_SAVE_VERSION", "SHAPE_CONTINENT", "SHAPE_RIVERLINE"];
  const functions = ["defaultProfile", "migrateLegacyBest", "migratePanelUnlocks", "loadProfile", "saveProfile", "loadRunSave", "saveRunSave", "clearRunSave"];
  vm.runInContext([...constants.map(extractConstant), ...functions.map(extractFunction), "let profile;"].join("\n"), context);
  return { values, run: (expression) => vm.runInContext(expression, context) };
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

test("save keys and schema changes require an explicit migration review", () => {
  const runtime = createStorageRuntime();
  assert.deepEqual(plain(runtime.run("[PROFILE_KEY, RUN_SAVE_KEY, PROFILE_VERSION, RUN_SAVE_VERSION]")), [profileKey, runKey, 1, 2]);
});

test("v3.68.0 profile survives loading and writing without lost progress", () => {
  const runtime = createStorageRuntime({ [profileKey]: JSON.stringify(profileFixture) });
  assert.deepEqual(plain(runtime.run("profile = loadProfile()")), profileFixture);
  runtime.run("saveProfile()");
  assert.deepEqual(JSON.parse(runtime.values.get(profileKey)), profileFixture);
});

test("v3.68.0 run survives storage round trip including recent stage fields", () => {
  const runtime = createStorageRuntime({ [runKey]: JSON.stringify(runFixture) });
  assert.deepEqual(plain(runtime.run("loadRunSave()")), runFixture);
  runtime.run("saveRunSave(loadRunSave())");
  assert.deepEqual(JSON.parse(runtime.values.get(runKey)), runFixture);
  // This tests serialization, not seed-to-settlement-index or resumeRun world compatibility.
});

test("older sparse profiles retain progress while newly introduced fields get defaults", () => {
  const oldProfile = { version: 1, crystals: 29, unlockedContinents: 3, options: { damageNumbers: false }, best: { kills: 120 } };
  const runtime = createStorageRuntime({ [profileKey]: JSON.stringify(oldProfile) });
  const profile = plain(runtime.run("loadProfile()"));
  assert.equal(profile.crystals, 29);
  assert.deepEqual(profile.best, { timeMs: 0, kills: 120 });
  assert.deepEqual(profile.options, { damageNumbers: false, dragonDamageNumbers: true });
  assert.deepEqual(profile.unlocks, { species: {}, specials: {}, regions: {} });
  assert.deepEqual(profile.unlockedPanels, { "0:0": true, "1:0": true, "2:0": true, "0:1": true, "1:1": true });
  assert.deepEqual(profile.evoSeen, {});
});

test("legacy best values migrate without deleting their source records", () => {
  const runtime = createStorageRuntime({ dragonTide_bestTimeMs: "123000", dragonTide_bestKills: "421" });
  assert.deepEqual(plain(runtime.run("loadProfile().best")), { timeMs: 123000, kills: 421 });
  assert.equal(runtime.values.get("dragonTide_bestTimeMs"), "123000");
  assert.equal(runtime.values.get("dragonTide_bestKills"), "421");
});

test("malformed JSON profiles fall back without crashing or erasing the raw record", () => {
  const runtime = createStorageRuntime({ [profileKey]: "{broken", dragonTide_bestKills: "42" });
  const profile = plain(runtime.run("loadProfile()"));
  assert.equal(profile.crystals, 0);
  assert.equal(profile.best.kills, 42);
  assert.equal(runtime.values.get(profileKey), "{broken");
});

test("missing, malformed, and incompatible run records do not resume or get deleted", () => {
  for (const raw of [null, "{broken", "null", JSON.stringify({ ...runFixture, version: 1 }), JSON.stringify({ ...runFixture, version: 3 })]) {
    const runtime = createStorageRuntime(raw === null ? {} : { [runKey]: raw });
    assert.equal(runtime.run("loadRunSave()"), null);
    assert.equal(runtime.values.get(runKey), raw ?? undefined);
  }
});

test("clearing a run preserves permanent profile progress", () => {
  const runtime = createStorageRuntime({ [profileKey]: JSON.stringify(profileFixture), [runKey]: JSON.stringify(runFixture) });
  runtime.run("clearRunSave()");
  assert.equal(runtime.values.has(runKey), false);
  assert.deepEqual(JSON.parse(runtime.values.get(profileKey)), profileFixture);
});

test("release builds disable debug entry points while prototypes keep them", () => {
  const registration = source.match(/^if \(!IS_RELEASE_BUILD\) \{[\s\S]*?^\}/m);
  assert.ok(registration, "Expected a guarded debug input registration block");
  for (const release of [false, true]) {
    const callbacks = [];
    const listeners = [];
    let advanced = 0;
    let rendered = 0;
    const context = vm.createContext({
      window: { ...(release ? { DRAGON_TIDE_RELEASE: { version: "3.68.0" } } : {}), addEventListener: (event, callback) => listeners.push({ event, callback }) },
      document: { getElementById: () => ({}) },
      dbgTap: (_element, callback) => callbacks.push(callback),
      debugAdvanceStage: () => { advanced++; },
      renderDebugPanel: () => { rendered++; },
      debugPanelEl: { classList: { add() {}, remove() {} } },
    });
    vm.runInContext([extractConstant("IS_RELEASE_BUILD"), "let debugPanelOpen = false;", extractFunction("toggleDebugPanel"), registration[0]].join("\n"), context);
    assert.equal(callbacks.length, release ? 0 : 1);
    assert.equal(listeners.length, release ? 0 : 1);
    if (!release) {
      callbacks[0]();
      listeners[0].callback({ key: "N" });
      assert.equal(advanced, 1);
      assert.equal(rendered, 1);
    } else {
      vm.runInContext("toggleDebugPanel(true)", context);
      assert.equal(vm.runInContext("debugPanelOpen", context), false);
      assert.equal(rendered, 0);
    }
  }
});
