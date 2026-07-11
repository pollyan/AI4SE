const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '../../');
const INTENT_TESTER_DIR = path.join(ROOT_DIR, 'tools', 'intent-tester');
const DIST_DIR = path.join(ROOT_DIR, 'dist');
const PROXY_DIST_DIR = path.join(DIST_DIR, 'intent-test-proxy');
const ZIP_FILE = path.join(DIST_DIR, 'intent-test-proxy.zip');
const FRONTEND_ZIP_FILE = path.join(
    INTENT_TESTER_DIR,
    'frontend',
    'static',
    'intent-test-proxy.zip'
);
const BROWSER_AUTOMATION_DIR = path.join(INTENT_TESTER_DIR, 'browser-automation');
const TEMPLATES_DIR = path.join(INTENT_TESTER_DIR, 'proxy_templates');
const REPRODUCIBLE_TIMESTAMP = new Date('2000-01-01T00:00:00.000Z');

const EXCLUDED_NAMES = new Set([
    '.DS_Store',
    '.pytest_cache',
    '__pycache__',
    'node_modules',
]);
const EXCLUDED_SUFFIXES = ['.pyc', '.pyo'];

function fail(message) {
    throw new Error(`Proxy package build failed: ${message}`);
}

function requireFile(filePath) {
    if (!fs.statSync(filePath, { throwIfNoEntry: false })?.isFile()) {
        fail(`required source file is missing: ${path.relative(ROOT_DIR, filePath)}`);
    }
}

function shouldExclude(name) {
    return EXCLUDED_NAMES.has(name) || EXCLUDED_SUFFIXES.some(suffix => name.endsWith(suffix));
}

function normalizeFile(filePath, mode = 0o644) {
    fs.chmodSync(filePath, mode);
    fs.utimesSync(filePath, REPRODUCIBLE_TIMESTAMP, REPRODUCIBLE_TIMESTAMP);
}

function copyFile(source, destination, mode = 0o644) {
    requireFile(source);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
    normalizeFile(destination, mode);
}

function copyDirectory(source, destination) {
    if (!fs.statSync(source, { throwIfNoEntry: false })?.isDirectory()) {
        fail(`required source directory is missing: ${path.relative(ROOT_DIR, source)}`);
    }

    fs.mkdirSync(destination, { recursive: true });
    for (const entry of fs.readdirSync(source, { withFileTypes: true })
        .sort((left, right) => left.name.localeCompare(right.name))) {
        if (shouldExclude(entry.name)) {
            continue;
        }
        const sourcePath = path.join(source, entry.name);
        const destinationPath = path.join(destination, entry.name);
        if (entry.isDirectory()) {
            copyDirectory(sourcePath, destinationPath);
        } else if (entry.isFile()) {
            copyFile(sourcePath, destinationPath);
        }
    }
}

function collectFiles(directory) {
    const files = [];
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })
        .sort((left, right) => left.name.localeCompare(right.name))) {
        const entryPath = path.join(directory, entry.name);
        if (entry.isDirectory()) {
            files.push(...collectFiles(entryPath));
        } else if (entry.isFile()) {
            files.push(entryPath);
        }
    }
    return files;
}

function writePackageJson() {
    const sourcePath = path.join(INTENT_TESTER_DIR, 'package.json');
    requireFile(sourcePath);
    const packageJson = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));
    packageJson.main = 'midscene_server.js';
    packageJson.scripts = {
        ...packageJson.scripts,
        start: 'node midscene_server.js',
    };
    const destination = path.join(PROXY_DIST_DIR, 'package.json');
    fs.writeFileSync(destination, `${JSON.stringify(packageJson, null, 2)}\n`, 'utf8');
    normalizeFile(destination);
}

function sha256(filePath) {
    return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function build() {
    fs.rmSync(PROXY_DIST_DIR, { recursive: true, force: true });
    fs.rmSync(ZIP_FILE, { force: true });
    fs.mkdirSync(PROXY_DIST_DIR, { recursive: true });

    copyFile(
        path.join(BROWSER_AUTOMATION_DIR, 'midscene_server.js'),
        path.join(PROXY_DIST_DIR, 'midscene_server.js')
    );
    writePackageJson();
    copyFile(
        path.join(INTENT_TESTER_DIR, 'package-lock.json'),
        path.join(PROXY_DIST_DIR, 'package-lock.json')
    );
    copyFile(
        path.join(TEMPLATES_DIR, 'start.sh'),
        path.join(PROXY_DIST_DIR, 'start.sh'),
        0o755
    );
    copyFile(
        path.join(TEMPLATES_DIR, 'start.bat'),
        path.join(PROXY_DIST_DIR, 'start.bat')
    );
    copyFile(
        path.join(TEMPLATES_DIR, '.env.example'),
        path.join(PROXY_DIST_DIR, '.env.example')
    );
    copyDirectory(
        path.join(INTENT_TESTER_DIR, 'midscene_framework'),
        path.join(PROXY_DIST_DIR, 'midscene_framework')
    );

    const archivePaths = collectFiles(PROXY_DIST_DIR)
        .map(filePath => path.relative(DIST_DIR, filePath))
        .sort();
    if (archivePaths.length === 0) {
        fail('package has no files');
    }

    execFileSync('zip', ['-X', '-q', ZIP_FILE, ...archivePaths], {
        cwd: DIST_DIR,
        env: { ...process.env, TZ: 'UTC' },
        stdio: 'inherit',
    });
    fs.mkdirSync(path.dirname(FRONTEND_ZIP_FILE), { recursive: true });
    fs.copyFileSync(ZIP_FILE, FRONTEND_ZIP_FILE);

    console.log(`Built ${path.relative(ROOT_DIR, ZIP_FILE)}`);
    console.log(`Synced ${path.relative(ROOT_DIR, FRONTEND_ZIP_FILE)}`);
    console.log(`SHA-256 ${sha256(ZIP_FILE)}`);
}

try {
    build();
} catch (error) {
    console.error(error.message);
    process.exit(1);
}
