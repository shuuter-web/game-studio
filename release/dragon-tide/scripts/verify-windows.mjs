import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function verifyWindowsContent(windowsRoot, manifest) {
  const expected = Object.fromEntries(Object.entries(manifest.windowsFiles ?? {}).filter(([name]) => name.startsWith('win-unpacked/')));
  if (!expected['win-unpacked/Dragon Tide.exe'] || !expected['win-unpacked/resources/app.asar']) throw new Error('Windows manifest is missing the executable or game archive');
  const actual = [];
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const filename = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new Error('Unexpected symbolic link in Steam content');
      if (entry.isDirectory()) walk(filename);
      else actual.push(path.relative(windowsRoot, filename).split(path.sep).join('/'));
    }
  }
  walk(path.join(windowsRoot, 'win-unpacked'));
  if (JSON.stringify(actual.sort()) !== JSON.stringify(Object.keys(expected).sort())) throw new Error('Windows content has missing or unexpected files; rebuild before Steam upload');
  for (const name of actual) {
    const hash = crypto.createHash('sha256').update(fs.readFileSync(path.join(windowsRoot, name))).digest('hex');
    if (hash !== expected[name]) throw new Error(`Windows content hash mismatch: ${name}`);
  }
}
