import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { ROOT, readRelease, requireRelease, run } from './shared.mjs';

// Signing material never enters the repository or the uploaded artifacts.
const signingDirectory = path.join(process.env.RUNNER_TEMP || os.tmpdir(), 'dragon-tide-ios-signing');
const stateFile = path.join(signingDirectory, 'state.json');
const projectFile = path.join(ROOT, 'ios/App/App.xcodeproj/project.pbxproj');
function security(args) {
  try {
    return execFileSync('/usr/bin/security', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch {
    // execFileSync errors include the full command, which can contain a password.
    throw new Error(`Apple security ${args[0]} failed. Check certificate/profile credentials and validity.`);
  }
}
function cleanup() {
  if (!fs.existsSync(stateFile)) return;
  const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
  if (state.originalKeychains) security(['list-keychains', '-d', 'user', '-s', ...state.originalKeychains]);
  const keychain = path.join(signingDirectory, 'build.keychain-db');
  if (fs.existsSync(keychain)) security(['delete-keychain', keychain]);
  if (state.profileUuid) {
    if (!/^[A-F0-9-]{36}$/i.test(state.profileUuid)) throw new Error('Invalid signing cleanup profile UUID');
    const profilePath = path.join(os.homedir(), 'Library/MobileDevice/Provisioning Profiles', `${state.profileUuid}.mobileprovision`);
    const previousProfile = path.join(signingDirectory, 'previous.mobileprovision');
    if (fs.existsSync(previousProfile)) fs.copyFileSync(previousProfile, profilePath);
    else fs.rmSync(profilePath, { force: true });
  }
  const previousProject = path.join(signingDirectory, 'project.pbxproj');
  if (fs.existsSync(previousProject)) fs.copyFileSync(previousProject, projectFile);
  fs.rmSync(signingDirectory, { recursive: true, force: true });
}

if (process.platform !== 'darwin') throw new Error('iOS signing requires macOS.');
if (process.argv[2] === 'cleanup') {
  cleanup();
} else if (process.argv[2] === 'build') {
  const release = readRelease();
  const { config } = release;
  requireRelease(release);
  const required = ['DT_IOS_CERTIFICATE_BASE64', 'DT_IOS_CERTIFICATE_PASSWORD', 'DT_IOS_PROFILE_BASE64', 'DT_IOS_TEAM_ID'];
  for (const name of required) if (!process.env[name]) throw new Error(`Missing ${name}`);
  const teamId = process.env.DT_IOS_TEAM_ID;
  if (!/^[A-Z0-9]{10}$/.test(teamId)) throw new Error('Invalid DT_IOS_TEAM_ID');
  if (!fs.existsSync(projectFile)) throw new Error('Run npm run mobile:sync -- ios --release first.');
  if (fs.existsSync(signingDirectory)) throw new Error('Previous signing state exists. Run node scripts/ios-signing.mjs cleanup first.');
  fs.mkdirSync(signingDirectory, { mode: 0o700 });
  const state = {};
  const saveState = () => fs.writeFileSync(stateFile, JSON.stringify(state), { mode: 0o600 });
  saveState();
  try {
    const certificatePath = path.join(signingDirectory, 'distribution.p12');
    const profilePath = path.join(signingDirectory, 'distribution.mobileprovision');
    const profilePlist = path.join(signingDirectory, 'profile.plist');
    const keychain = path.join(signingDirectory, 'build.keychain-db');
    fs.writeFileSync(certificatePath, Buffer.from(process.env.DT_IOS_CERTIFICATE_BASE64, 'base64'), { mode: 0o600 });
    fs.writeFileSync(profilePath, Buffer.from(process.env.DT_IOS_PROFILE_BASE64, 'base64'), { mode: 0o600 });
    fs.writeFileSync(profilePlist, security(['cms', '-D', '-i', profilePath]), { mode: 0o600 });
    const plist = (key) => execFileSync('/usr/libexec/PlistBuddy', ['-c', `Print :${key}`, profilePlist], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
    const profileUuid = plist('UUID');
    if (!/^[A-F0-9-]{36}$/i.test(profileUuid)) throw new Error('Invalid provisioning profile UUID');
    if (plist('TeamIdentifier:0') !== teamId || plist('Entitlements:application-identifier') !== `${teamId}.${config.appId}`) {
      throw new Error('The provisioning profile must match the permanent appId and Apple team.');
    }
    if (plist('Entitlements:get-task-allow') !== 'false') throw new Error('An App Store distribution profile is required.');
    const profileDirectory = path.join(os.homedir(), 'Library/MobileDevice/Provisioning Profiles');
    fs.mkdirSync(profileDirectory, { recursive: true });
    const installedProfile = path.join(profileDirectory, `${profileUuid}.mobileprovision`);
    if (fs.existsSync(installedProfile)) fs.copyFileSync(installedProfile, path.join(signingDirectory, 'previous.mobileprovision'));
    state.profileUuid = profileUuid;
    saveState();
    fs.copyFileSync(profilePath, installedProfile);

    state.originalKeychains = [...security(['list-keychains', '-d', 'user']).matchAll(/"([^"]+)"/g)].map((match) => match[1]);
    saveState();
    const keychainPassword = crypto.randomBytes(32).toString('hex');
    security(['create-keychain', '-p', keychainPassword, keychain]);
    security(['set-keychain-settings', '-lut', '21600', keychain]);
    security(['unlock-keychain', '-p', keychainPassword, keychain]);
    security(['import', certificatePath, '-P', process.env.DT_IOS_CERTIFICATE_PASSWORD, '-k', keychain, '-T', '/usr/bin/codesign', '-T', '/usr/bin/security']);
    security(['set-key-partition-list', '-S', 'apple-tool:,apple:,codesign:', '-s', '-k', keychainPassword, keychain]);
    security(['list-keychains', '-d', 'user', '-s', keychain, ...state.originalKeychains]);
    const identities = [...security(['find-identity', '-v', '-p', 'codesigning', keychain]).matchAll(/\d+\) ([A-F0-9]{40}) "(?:Apple|iPhone) Distribution:[^"]+"/g)];
    if (identities.length !== 1) throw new Error('The P12 must contain exactly one valid Apple Distribution signing identity and its private key.');
    const signingCertificate = identities[0][1];

    // Configure only the app target; global provisioning settings break Swift package targets.
    const originalProject = fs.readFileSync(projectFile, 'utf8');
    const bundleExpression = /PRODUCT_BUNDLE_IDENTIFIER = [^;]+;/g;
    if ([...originalProject.matchAll(bundleExpression)].length !== 2) throw new Error('Unexpected Xcode app configurations; update the signing patch.');
    fs.copyFileSync(projectFile, path.join(signingDirectory, 'project.pbxproj'));
    fs.writeFileSync(projectFile, originalProject
      .replace(/CODE_SIGN_STYLE = (Automatic|Manual);/g, 'CODE_SIGN_STYLE = Manual;')
      .replace(bundleExpression, `PRODUCT_BUNDLE_IDENTIFIER = ${config.appId};\n\t\t\t\tDEVELOPMENT_TEAM = ${teamId};\n\t\t\t\tCODE_SIGN_IDENTITY = "${signingCertificate}";\n\t\t\t\tPROVISIONING_PROFILE_SPECIFIER = "${profileUuid}";`));
    const outputDirectory = path.join(ROOT, 'dist/ios');
    fs.mkdirSync(outputDirectory, { recursive: true });
    const archivePath = path.join(outputDirectory, 'DragonTide.xcarchive');
    run('xcodebuild', ['-project', 'ios/App/App.xcodeproj', '-scheme', 'App', '-configuration', 'Release', '-destination', 'generic/platform=iOS', '-archivePath', archivePath, 'archive']);
    const exportOptions = path.join(signingDirectory, 'ExportOptions.plist');
    fs.writeFileSync(exportOptions, `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>method</key><string>app-store-connect</string>
<key>destination</key><string>export</string>
<key>signingStyle</key><string>manual</string>
<key>teamID</key><string>${teamId}</string>
<key>signingCertificate</key><string>${signingCertificate}</string>
<key>manageAppVersionAndBuildNumber</key><false/>
<key>provisioningProfiles</key><dict><key>${config.appId}</key><string>${profileUuid}</string></dict>
</dict></plist>\n`);
    run('xcodebuild', ['-exportArchive', '-archivePath', archivePath, '-exportPath', path.join(outputDirectory, 'export'), '-exportOptionsPlist', exportOptions]);
    if (!fs.readdirSync(path.join(outputDirectory, 'export')).some((file) => file.endsWith('.ipa'))) throw new Error('Xcode did not produce a signed IPA.');
    console.log('Signed App Store IPA exported. No store upload or publication was performed.');
  } finally {
    cleanup();
  }
} else {
  throw new Error('Usage: node scripts/ios-signing.mjs build|cleanup');
}
