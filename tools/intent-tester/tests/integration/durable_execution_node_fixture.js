'use strict';

const Module = require('module');
const path = require('path');

const productionServerPath = path.resolve(process.argv[2]);
const listenPort = Number(process.argv[3]);
const blockedNavigationMs = Number(process.env.BLOCKED_NAVIGATION_MS || 1200);

if (!productionServerPath || !Number.isInteger(listenPort) || listenPort < 1) {
    throw new Error('usage: durable_execution_node_fixture.js <server-path> <port>');
}

function delay(delayMs) {
    return new Promise((resolve) => setTimeout(resolve, delayMs));
}

function createFakePage() {
    return {
        setDefaultTimeout() {},
        setDefaultNavigationTimeout() {},
        async goto(url) {
            if (String(url).includes('/blocked')) {
                await delay(blockedNavigationMs);
            }
            return null;
        },
        async waitForTimeout() {},
        async screenshot() {
            return Buffer.from('offline-fake-screenshot');
        },
        async close() {},
        url() {
            return 'http://fixture.invalid/';
        },
        async title() {
            return 'Offline fixture';
        },
        viewportSize() {
            return { width: 1280, height: 720 };
        }
    };
}

const fakePlaywright = {
    chromium: {
        async launch() {
            return {
                async newContext() {
                    return {
                        async newPage() {
                            return createFakePage();
                        }
                    };
                },
                async close() {}
            };
        }
    }
};

class FakePlaywrightAgent {
    constructor(page, config) {
        this.page = page;
        this.config = config;
    }
}

const originalLoad = Module._load;
Module._load = function loadWithExternalAdaptersFaked(request, parent, isMain) {
    if (request === 'playwright') {
        return fakePlaywright;
    }
    if (request === '@midscene/web') {
        return { PlaywrightAgent: FakePlaywrightAgent };
    }
    return originalLoad.call(this, request, parent, isMain);
};

const productionRuntime = require(productionServerPath);
let shuttingDown = false;

async function shutdown() {
    if (shuttingDown) {
        return;
    }
    shuttingDown = true;
    await productionRuntime.resetState();
    await productionRuntime.closeServer();
}

process.once('SIGTERM', () => {
    shutdown().then(() => process.exit(0)).catch(() => process.exit(1));
});
process.once('SIGINT', () => {
    shutdown().then(() => process.exit(0)).catch(() => process.exit(1));
});

productionRuntime.startServer(listenPort).catch((error) => {
    console.error(error);
    process.exit(1);
});
