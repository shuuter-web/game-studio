import fs from 'node:fs';
import path from 'node:path';
import { ROOT, readRelease, requireRelease } from './shared.mjs';

const release = readRelease();
const { config, version, buildNumber, commit } = release;
requireRelease(release);
const appId = String(config.steam.appId ?? '');
const depotId = String(config.steam.windowsDepotId ?? '');
if (!/^[1-9]\d*$/.test(appId) || !/^[1-9]\d*$/.test(depotId)) {
  throw new Error('Set the Steam App ID and Windows depot ID in config.json.');
}
const contentDirectory = path.join(ROOT, 'dist/windows/win-unpacked');
if (!fs.existsSync(path.join(contentDirectory, 'Dragon Tide.exe'))) {
  throw new Error('Build Windows first: npm run build:windows');
}
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'dist/windows/build-manifest.json'), 'utf8'));
if (manifest.version !== version || manifest.buildNumber !== buildNumber || manifest.commit !== commit || manifest.sourceDirty !== false || manifest.appId !== config.appId || manifest.identityConfirmed !== true) {
  throw new Error('Windows output does not match this clean release tag. Rebuild Windows from the tagged commit.');
}
const outputDirectory = path.join(ROOT, 'dist/steam');
fs.mkdirSync(outputDirectory, { recursive: true });
// VDF paths are relative to the generated script. Never mark a public branch live automatically.
fs.writeFileSync(path.join(outputDirectory, `app_build_${appId}.vdf`), `"AppBuild"
{
  "AppID" "${appId}"
  "Desc" "Dragon Tide ${version} build ${buildNumber} ${commit}"
  "BuildOutput" "./cache"
  "ContentRoot" "../windows/win-unpacked"
  "Preview" "0"
  "Depots"
  {
    "${depotId}" "depot_build_${depotId}.vdf"
  }
}
`);
fs.writeFileSync(path.join(outputDirectory, `depot_build_${depotId}.vdf`), `"DepotBuildConfig"
{
  "DepotID" "${depotId}"
  "FileMapping"
  {
    "LocalPath" "*"
    "DepotPath" "."
    "recursive" "1"
  }
  "FileExclusion" "*.pdb"
  "FileExclusion" "*.log"
}
`);
console.log(`SteamPipe scripts generated in ${outputDirectory}. Upload using SteamCMD; choose the live branch in Steamworks.`);
