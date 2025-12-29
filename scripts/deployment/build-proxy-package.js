const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '../../');
const DIST_DIR = path.join(ROOT_DIR, 'dist');
const PROXY_DIST_DIR = path.join(DIST_DIR, 'intent-test-proxy');
const ZIP_FILE = path.join(DIST_DIR, 'intent-test-proxy.zip');

console.log(`ROOT_DIR: ${ROOT_DIR}`);
console.log(`DIST_DIR: ${DIST_DIR}`);

// 1. Clean/Create dist directories
if (fs.existsSync(PROXY_DIST_DIR)) {
    fs.rmSync(PROXY_DIST_DIR, { recursive: true, force: true });
}
if (fs.existsSync(ZIP_FILE)) {
    fs.rmSync(ZIP_FILE);
}
fs.mkdirSync(PROXY_DIST_DIR, { recursive: true });

// 2. Copy core files from browser-automation
const BROWSER_AUTOMATION_DIR = path.join(ROOT_DIR, 'tools', 'intent-tester', 'browser-automation');

const coreFiles = [
    { src: path.join(BROWSER_AUTOMATION_DIR, 'midscene_server.js'), dest: 'midscene_server.js' },
    { src: path.join(ROOT_DIR, 'package.json'), dest: 'package.json' }
];

coreFiles.forEach(({ src, dest }) => {
    const destPath = path.join(PROXY_DIST_DIR, dest);
    if (fs.existsSync(src)) {
        fs.copyFileSync(src, destPath);
        console.log(`Copied ${dest}`);
    } else {
        console.warn(`Warning: ${src} not found.`);
    }
});

// Copy start scripts from templates
const templatesDir = path.join(ROOT_DIR, 'scripts', 'proxy_templates');
const startScripts = ['start.sh', 'start.bat'];

startScripts.forEach(file => {
    const src = path.join(templatesDir, file);
    const dest = path.join(PROXY_DIST_DIR, file);
    if (fs.existsSync(src)) {
        fs.copyFileSync(src, dest);
        console.log(`Copied ${file} from templates`);
    } else {
        console.warn(`Warning: ${file} not found in ${templatesDir}.`);
    }
});

// 3. Copy directory recursively
function copyDir(src, dest) {
    if (!fs.existsSync(src)) return;
    fs.mkdirSync(dest, { recursive: true });
    const entries = fs.readdirSync(src, { withFileTypes: true });

    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);

        if (entry.isDirectory()) {
            copyDir(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

const dirsToCopy = [
    { src: path.join(BROWSER_AUTOMATION_DIR, 'midscene_framework'), dest: 'midscene_framework' }
];
dirsToCopy.forEach(({ src, dest }) => {
    copyDir(src, path.join(PROXY_DIST_DIR, dest));
    console.log(`Copied directory ${dest}`);
});

// 4. Create ZIP
console.log('Creating ZIP package...');
try {
    // Check if zip command exists (usually available in unix environments)
    execSync(`cd "${DIST_DIR}" && zip -r intent-test-proxy.zip intent-test-proxy`);
    console.log(`Successfully created ${ZIP_FILE}`);
} catch (error) {
    console.error('Failed to create zip using command line zip tool. Trying internal logic if needed or just fail.', error);
    // Fallback or exit? For now exit as CI usually has zip. 
    process.exit(1);
}
