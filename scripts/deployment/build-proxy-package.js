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

// 2. Copy core files
const filesFromRoot = [
    'midscene_server.js',
    'package.json'
];

filesFromRoot.forEach(file => {
    const src = path.join(ROOT_DIR, file);
    const dest = path.join(PROXY_DIST_DIR, file);
    if (fs.existsSync(src)) {
        fs.copyFileSync(src, dest);
        console.log(`Copied ${file} from root`);
    } else {
        console.warn(`Warning: ${file} not found in root.`);
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

const dirsToCopy = ['midscene_framework'];
dirsToCopy.forEach(dir => {
    copyDir(path.join(ROOT_DIR, dir), path.join(PROXY_DIST_DIR, dir));
    console.log(`Copied directory ${dir}`);
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
