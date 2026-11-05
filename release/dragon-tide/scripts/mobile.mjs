import fs from 'node:fs';
import path from 'node:path';
import { ROOT, readRelease, requireRelease, run } from './shared.mjs';

const [platform, ...flags] = process.argv.slice(2);
if (!['android', 'ios'].includes(platform) || flags.some((flag) => flag !== '--release')) {
  throw new Error('Usage: npm run mobile:sync -- android|ios [--release]');
}
const release = readRelease();
const { config, version, buildNumber } = release;
if (flags.includes('--release')) requireRelease(release);
if (platform === 'ios' && process.platform !== 'darwin') {
  throw new Error('iOS generation requires macOS with Xcode 26 or later. Use the iOS CI job on Windows.');
}
const nativeDirectory = path.join(ROOT, platform);
const identityFile = path.join(nativeDirectory, '.dragon-tide-identity.json');
const capacitorFile = path.join(ROOT, 'capacitor.config.json');
const capacitorConfig = JSON.parse(fs.readFileSync(capacitorFile, 'utf8'));
// These origins identify localStorage. Changing them would make existing saves invisible.
const requiredServer = { hostname: 'localhost', iosScheme: 'capacitor', androidScheme: 'https' };
if (Object.keys(capacitorConfig.server ?? {}).length !== 3 || Object.entries(requiredServer).some(([key, value]) => capacitorConfig.server?.[key] !== value)) {
  throw new Error('Capacitor storage origins must stay fixed; a migration is required to change server settings.');
}
if (fs.existsSync(nativeDirectory)) {
  if (!fs.existsSync(identityFile) || JSON.parse(fs.readFileSync(identityFile, 'utf8')).appId !== config.appId) {
    throw new Error(`The generated ${platform} project has an unknown/different appId. Preserve any needed local work, then regenerate this ignored directory.`);
  }
}
if (capacitorConfig.appId !== config.appId) {
  capacitorConfig.appId = config.appId;
  fs.writeFileSync(capacitorFile, `${JSON.stringify(capacitorConfig, null, 2)}\n`);
}
run(process.execPath, [path.join(ROOT, 'scripts/build-web.mjs')], { cwd: ROOT });
const capacitorCli = path.join(ROOT, 'node_modules/@capacitor/cli/bin/capacitor');
if (!fs.existsSync(nativeDirectory)) {
  run(process.execPath, [capacitorCli, 'add', platform], { cwd: ROOT });
  fs.writeFileSync(identityFile, `${JSON.stringify({ appId: config.appId }, null, 2)}\n`);
}
run(process.execPath, [capacitorCli, 'sync', platform], { cwd: ROOT });

function replaceRequired(source, expression, replacement, label) {
  if (!expression.test(source)) throw new Error(`Capacitor template changed: cannot locate ${label}.`);
  return source.replace(expression, replacement);
}

if (platform === 'android') {
  const gradleFile = path.join(nativeDirectory, 'app/build.gradle');
  let gradle = fs.readFileSync(gradleFile, 'utf8');
  gradle = replaceRequired(gradle, /versionCode\s+\d+/g, `versionCode ${buildNumber}`, 'versionCode');
  gradle = replaceRequired(gradle, /versionName\s+"[^"]+"/g, `versionName "${version}"`, 'versionName');
  // The generated project may be rebuilt locally. Replace the managed block instead of appending it twice.
  gradle = gradle.replace(/\n\/\/ BEGIN DRAGON TIDE SIGNING[\s\S]*?\/\/ END DRAGON TIDE SIGNING\n?/g, '\n');
  gradle += `
// BEGIN DRAGON TIDE SIGNING
// Secrets remain in the environment; no keystore or password is copied into app resources.
def dragonTideSigningNames = ['DT_ANDROID_KEYSTORE_PATH', 'DT_ANDROID_KEYSTORE_PASSWORD', 'DT_ANDROID_KEY_ALIAS', 'DT_ANDROID_KEY_PASSWORD']
def dragonTideSigningValues = dragonTideSigningNames.collect { System.getenv(it) }
if (dragonTideSigningValues.any { it } && !dragonTideSigningValues.every { it }) {
    throw new GradleException('All DT_ANDROID_* signing environment variables are required together.')
}
if (dragonTideSigningValues.any { it } && ${config.identityConfirmed !== true}) {
    throw new GradleException('Confirm the permanent app identity in config.json and run mobile:sync before signing.')
}
if (dragonTideSigningValues.every { it }) {
    android.signingConfigs.create('dragonTideRelease') {
        storeFile file(System.getenv('DT_ANDROID_KEYSTORE_PATH'))
        storePassword System.getenv('DT_ANDROID_KEYSTORE_PASSWORD')
        keyAlias System.getenv('DT_ANDROID_KEY_ALIAS')
        keyPassword System.getenv('DT_ANDROID_KEY_PASSWORD')
    }
    android.buildTypes.release.signingConfig = android.signingConfigs.dragonTideRelease
}
// END DRAGON TIDE SIGNING
`;
  fs.writeFileSync(gradleFile, gradle);
} else {
  const projectFile = path.join(nativeDirectory, 'App/App.xcodeproj/project.pbxproj');
  let project = fs.readFileSync(projectFile, 'utf8');
  project = replaceRequired(project, /MARKETING_VERSION = [^;]+;/g, `MARKETING_VERSION = ${version};`, 'MARKETING_VERSION');
  project = replaceRequired(project, /CURRENT_PROJECT_VERSION = [^;]+;/g, `CURRENT_PROJECT_VERSION = ${buildNumber};`, 'CURRENT_PROJECT_VERSION');
  fs.writeFileSync(projectFile, project);
}
console.log(`Prepared ${platform}: ${config.appId}, version ${version}, build ${buildNumber}. Native signing/build is a separate step.`);
