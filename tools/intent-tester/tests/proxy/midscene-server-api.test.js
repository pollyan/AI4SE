/** Production HTTP API contract tests for the MidScene Node server. */

const rawRequest = require('supertest');
const fs = require('fs');
const os = require('os');
const path = require('path');

const CANARY_TOKEN = 'qs04-canary-proxy-token-0123456789abcdef';
const PUBLIC_ORIGIN = 'http://127.0.0.1:5001';
const bearer = `Bearer ${CANARY_TOKEN}`;
function request(app) {
  const client = rawRequest(app);
  return new Proxy(client, {
    get(target, property) {
      if (['get', 'post', 'put', 'patch', 'delete'].includes(property)) {
        return route => target[property](route).set('Authorization', bearer);
      }
      return target[property];
    }
  });
}

const mockHttpClient = {
  post: jest.fn().mockResolvedValue({ status: 200, data: {} })
};

let releaseBlockedNavigation;
const mockPage = {
  setDefaultTimeout: jest.fn(),
  setDefaultNavigationTimeout: jest.fn(),
  goto: jest.fn().mockImplementation(url => {
    if (url === 'https://blocked.example') {
      return new Promise(resolve => {
        releaseBlockedNavigation = resolve;
      });
    }
    return Promise.resolve();
  }),
  waitForTimeout: jest.fn().mockResolvedValue(undefined),
  screenshot: jest.fn().mockResolvedValue(Buffer.from('screenshot')),
  close: jest.fn().mockResolvedValue(undefined)
};

const mockBrowser = {
  newContext: jest.fn().mockResolvedValue({
    newPage: jest.fn().mockResolvedValue(mockPage),
    close: jest.fn().mockResolvedValue(undefined)
  }),
  close: jest.fn().mockResolvedValue(undefined)
};

function createAutomationResource(pageOverrides = {}, browserOverrides = {}) {
  const ownedPage = {
    setDefaultTimeout: jest.fn(),
    setDefaultNavigationTimeout: jest.fn(),
    goto: jest.fn().mockResolvedValue(undefined),
    waitForTimeout: jest.fn().mockResolvedValue(undefined),
    screenshot: jest.fn().mockResolvedValue(Buffer.from('screenshot')),
    close: jest.fn().mockResolvedValue(undefined),
    ...pageOverrides
  };
  const ownedBrowser = {
    newContext: jest.fn().mockResolvedValue({
      newPage: jest.fn().mockResolvedValue(ownedPage),
      close: jest.fn().mockResolvedValue(undefined)
    }),
    close: jest.fn().mockResolvedValue(undefined),
    ...browserOverrides
  };
  return { page: ownedPage, browser: ownedBrowser };
}

jest.mock('@midscene/web', () => ({
  PlaywrightAgent: jest.fn().mockImplementation(() => ({}))
}));
jest.mock('playwright', () => ({
  chromium: { launch: jest.fn().mockResolvedValue(mockBrowser) }
}));
const { chromium } = require('playwright');
process.env.OPENAI_API_KEY = 'test-api-key';
process.env.OPENAI_BASE_URL = 'https://test-api.example/v1';
process.env.MIDSCENE_MODEL_NAME = 'test-model';
process.env.MAIN_APP_URL = 'http://flask.example/api';
process.env.NODE_ENV = 'test';
process.env.INTENT_PROXY_TOPOLOGY = 'local-host';
process.env.INTENT_PROXY_TOKEN = CANARY_TOKEN;
process.env.INTENT_PUBLIC_ORIGIN = PUBLIC_ORIGIN;

const productionServer = require('../../browser-automation/midscene_server');

const testcase = url => ({
  id: 1,
  name: `API contract ${url}`,
  steps: [{ type: 'navigate', params: { url } }]
});

async function waitForRunning(executionId) {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    if (productionServer.executionStates.get(executionId)?.status === 'running') {
      return;
    }
    await new Promise(resolve => setImmediate(resolve));
  }
  throw new Error(`Execution ${executionId} did not start`);
}

async function waitForReady() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    const status = await request(productionServer.app).get('/api/status').set('Authorization', bearer);
    if (status.body.status === 'ready') {
      return;
    }
    await new Promise(resolve => setImmediate(resolve));
  }
  throw new Error('Production execution runtime did not become ready');
}

describe('MidScene production HTTP API', () => {
  beforeEach(async () => {
    await productionServer.resetState();
    releaseBlockedNavigation = undefined;
    mockHttpClient.post.mockReset().mockResolvedValue({ status: 200, data: {} });
    productionServer.setLifecycleHttpClient(mockHttpClient);
    chromium.launch.mockReset().mockResolvedValue(mockBrowser);
    mockPage.goto.mockClear();
    mockPage.close.mockReset().mockResolvedValue(undefined);
    mockBrowser.close.mockClear();
  });

  afterEach(async () => {
    releaseBlockedNavigation?.();
    await productionServer.resetState();
  });

  afterAll(async () => {
    releaseBlockedNavigation?.();
    await productionServer.closeServer();
  });

  test.each([
    [{ INTENT_PROXY_TOPOLOGY: 'local-host', INTENT_PROXY_TOKEN: '', INTENT_PUBLIC_ORIGIN: PUBLIC_ORIGIN }, /token/i],
    [{ INTENT_PROXY_TOPOLOGY: 'local-host', INTENT_PROXY_TOKEN: 'too-short', INTENT_PUBLIC_ORIGIN: PUBLIC_ORIGIN }, /32/],
    [{ INTENT_PROXY_TOPOLOGY: 'implicit', INTENT_PROXY_TOKEN: CANARY_TOKEN, INTENT_PUBLIC_ORIGIN: PUBLIC_ORIGIN }, /topology/i],
    [{ INTENT_PROXY_TOPOLOGY: 'local-host', INTENT_PROXY_TOKEN: CANARY_TOKEN, INTENT_PUBLIC_ORIGIN: '*' }, /origin/i],
    [{ INTENT_PROXY_TOPOLOGY: 'local-host', INTENT_PROXY_TOKEN: CANARY_TOKEN, INTENT_PUBLIC_ORIGIN: 'http://localhost.evil.example' }, /loopback/i],
    [{ INTENT_PROXY_TOPOLOGY: 'local-host', INTENT_PROXY_TOKEN: CANARY_TOKEN, INTENT_PUBLIC_ORIGIN: 'http://evil.example' }, /loopback/i],
    [{ INTENT_PROXY_TOPOLOGY: 'local-host', INTENT_PROXY_TOKEN: CANARY_TOKEN, INTENT_PUBLIC_ORIGIN: 'https://127.0.0.1:5001' }, /loopback/i]
  ])('runtime config fails closed for invalid security environment %#', (env, expected) => {
    expect(() => productionServer.loadRuntimeConfig(env)).toThrow(expected);
  });

  test('runtime topology derives the only allowed bind and socket policy', () => {
    expect(productionServer.loadRuntimeConfig({
      INTENT_PROXY_TOPOLOGY: 'local-host',
      INTENT_PROXY_TOKEN: CANARY_TOKEN,
      INTENT_PUBLIC_ORIGIN: PUBLIC_ORIGIN
    })).toEqual({
      topology: 'local-host',
      bindHost: '127.0.0.1',
      browserSocketEnabled: true,
      publicOrigin: PUBLIC_ORIGIN,
      proxyToken: CANARY_TOKEN
    });
    expect(productionServer.loadRuntimeConfig({
      INTENT_PROXY_TOPOLOGY: 'managed',
      INTENT_PROXY_TOKEN: CANARY_TOKEN,
      INTENT_PUBLIC_ORIGIN: PUBLIC_ORIGIN
    })).toMatchObject({ topology: 'managed', bindHost: '0.0.0.0', browserSocketEnabled: false });
    expect(productionServer.loadRuntimeConfig({
      INTENT_PROXY_TOPOLOGY: 'local-host',
      INTENT_PROXY_TOKEN: CANARY_TOKEN,
      INTENT_PUBLIC_ORIGIN: 'http://[::1]:5001'
    })).toMatchObject({ topology: 'local-host', publicOrigin: 'http://[::1]:5001' });
  });

  test('health is the only anonymous route and bearer failures are stable and secret-free', async () => {
    const health = await rawRequest(productionServer.app).get('/health');
    const missing = await rawRequest(productionServer.app).get('/api/status');
    const wrong = await rawRequest(productionServer.app)
      .get('/api/status')
      .set('Authorization', `Bearer wrong-${CANARY_TOKEN}`);
    const accepted = await request(productionServer.app)
      .get('/api/status')
      .set('Authorization', bearer);

    expect(health.status).toBe(200);
    expect(Object.keys(health.body).sort()).toEqual(['status', 'success']);
    expect(JSON.stringify(health.body)).not.toContain(CANARY_TOKEN);
    for (const response of [missing, wrong]) {
      expect(response.status).toBe(401);
      expect(response.body).toEqual({ success: false, code: 'PROXY_AUTH_REQUIRED' });
      expect(JSON.stringify(response.body)).not.toContain(CANARY_TOKEN);
    }
    expect(accepted.status).toBe(200);
  });

  test('side-effect GET /ai-test does not exist and POST requires bearer', async () => {
    const getResponse = await rawRequest(productionServer.app).get('/ai-test');
    const postResponse = await rawRequest(productionServer.app).post('/ai-test').send({});
    expect(getResponse.status).toBe(404);
    expect(postResponse.status).toBe(401);
    expect(postResponse.body).toEqual({ success: false, code: 'PROXY_AUTH_REQUIRED' });
  });

  test('execution status exposes only the safe contract', async () => {
    productionServer.executionStates.set('safe-status', {
      id: 'safe-status', status: 'failed', currentStep: 2, totalSteps: 5,
      steps: [{
        index: 1,
        description: 'Safe progress',
        status: 'success',
        start_time: '2026-07-11T01:00:00.000Z',
        end_time: '2026-07-11T01:00:01.000Z',
        duration: 1000,
        params: { password: CANARY_TOKEN },
        error_message: `raw ${CANARY_TOKEN}`,
        screenshot: '/tmp/private.png'
      }],
      callbackErrors: [{ event: 'result', code: 'callback_failed', attempts: 3 }],
      logs: ['secret log'], params: { password: CANARY_TOKEN }, screenshots: ['/tmp/private.png'],
      error: `raw ${CANARY_TOKEN}`
    });
    const response = await request(productionServer.app)
      .get('/api/execution-status/safe-status')
      .set('Authorization', bearer);
    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      success: true,
      executionId: 'safe-status',
      status: 'failed',
      progress: { currentStep: 2, totalSteps: 5 },
      steps: [{
        index: 1,
        description: 'Safe progress',
        status: 'success',
        start_time: '2026-07-11T01:00:00.000Z',
        end_time: '2026-07-11T01:00:01.000Z',
        duration: 1000
      }],
      callbackCodes: ['callback_failed']
    });
    expect(JSON.stringify(response.body)).not.toContain(CANARY_TOKEN);
  });

  test('artifact paths cannot escape the owning output root', () => {
    const outputRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'qs04-output-'));
    const outsideRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'qs04-outside-'));
    expect(productionServer.resolveArtifactPath(outputRoot, 'execution-1', 'report.html'))
      .toBe(path.join(outputRoot, 'execution-1', 'report.html'));
    for (const [executionId, serverName] of [['../escape', 'x.png'], ['execution-1', '../../escape.png']]) {
      expect(() => productionServer.resolveArtifactPath(outputRoot, executionId, serverName))
        .toThrow(/artifact path/i);
    }
    fs.symlinkSync(outsideRoot, path.join(outputRoot, 'execution-link'), 'dir');
    expect(() => productionServer.resolveArtifactPath(outputRoot, 'execution-link', 'report.html'))
      .toThrow(/artifact path/i);
    fs.rmSync(outputRoot, { recursive: true, force: true });
    fs.rmSync(outsideRoot, { recursive: true, force: true });
  });

  test('report discovery and generated reports stay inside the execution owning root', async () => {
    const outputRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'qs04-report-output-'));
    const ownReportDir = path.join(outputRoot, 'execution-a', 'report');
    const foreignReportDir = path.join(outputRoot, 'execution-b', 'report');
    fs.mkdirSync(ownReportDir, { recursive: true });
    fs.mkdirSync(foreignReportDir, { recursive: true });
    const ownReport = path.join(ownReportDir, 'playwright-own.html');
    const foreignReport = path.join(foreignReportDir, 'playwright-foreign.html');
    fs.writeFileSync(
      ownReport,
      '<html><body>own report<script>globalThis.__reportXss = 1</script></body></html>'
    );
    fs.writeFileSync(foreignReport, '<html><body>foreign report</body></html>');
    const future = new Date(Date.now() + 5000);
    fs.utimesSync(foreignReport, future, future);

    expect(productionServer.findLatestExecutionReport(outputRoot, 'execution-a')).toBe(ownReport);
    const generated = await productionServer.generateSimplifiedReport(
      ownReport,
      { name: 'Scoped report <img src=x onerror="globalThis.__reportXss = 2">' },
      { status: 'success', steps: [], duration: 1 },
      outputRoot,
      'execution-a'
    );
    expect(generated).toBe(path.join(ownReportDir, 'playwright-own_simplified.html'));
    const generatedContent = fs.readFileSync(generated, 'utf8');
    expect(generatedContent).toContain('own report');
    expect(generatedContent).not.toContain('foreign report');
    expect(generatedContent).toContain('&lt;img src=x onerror=');
    expect(generatedContent).toContain('&lt;script&gt;globalThis.__reportXss = 1&lt;/script&gt;');
    expect(generatedContent).not.toMatch(/<script|<img/i);
    expect(generatedContent).toContain("default-src 'none'");
    await expect(productionServer.generateSimplifiedReport(
      foreignReport,
      { name: 'Wrong owner' },
      { status: 'success', steps: [] },
      outputRoot,
      'execution-a'
    )).rejects.toThrow(/artifact path/i);
    fs.rmSync(outputRoot, { recursive: true, force: true });
  });

  test.each([
    {},
    { executionId: '' },
    { executionId: '   ' },
    { executionId: 42 },
    { executionId: {} }
  ])('POST /api/execute-testcase rejects missing or invalid executionId: %p', async invalidId => {
    const response = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ ...invalidId, testcase: testcase('https://example.com') });

    expect(response.status).toBe(400);
    expect(response.body.success).toBe(false);
    expect(response.body.error).toMatch(/executionId/);
  });

  test('duplicate active executionId and concurrent different execution are explicitly rejected', async () => {
    const firstId = 'serial-execution';
    const first = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: firstId, testcase: testcase('https://blocked.example') });
    expect(first.status).toBe(200);
    await waitForRunning(firstId);

    const busyStatus = await request(productionServer.app).get('/api/status');
    expect(busyStatus.body).toMatchObject({
      status: 'busy',
      activeExecutionId: firstId
    });

    const duplicate = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: firstId, testcase: testcase('https://example.com') });
    const concurrent = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: 'other-execution', testcase: testcase('https://example.com') });

    expect(duplicate.status).toBe(409);
    expect(concurrent.status).toBe(409);
    expect(productionServer.executionStates.has('other-execution')).toBe(false);
  });

  test('stop rejects terminal, non-active and control-less executions without mutating the active owner', async () => {
    const finishedId = 'finished-execution';
    await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: finishedId, testcase: testcase('https://example.com') });
    await waitForReady();
    expect(productionServer.executionStates.get(finishedId).status).toBe('success');

    const activeId = 'active-execution';
    await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: activeId, testcase: testcase('https://blocked.example') });
    await waitForRunning(activeId);
    mockBrowser.close.mockClear();

    const stopFinished = await request(productionServer.app)
      .post(`/api/stop-execution/${finishedId}`);

    expect(stopFinished.status).toBe(409);
    expect(stopFinished.body.success).toBe(false);
    expect(productionServer.executionStates.get(finishedId).status).toBe('success');
    expect(productionServer.executionStates.get(activeId).status).toBe('running');
    expect(productionServer.executionControls.get(activeId).shouldStop).toBe(false);
    expect(mockBrowser.close).not.toHaveBeenCalled();

    productionServer.executionStates.set('foreign-running', {
      id: 'foreign-running',
      status: 'running',
      startTime: new Date(),
      steps: [],
      screenshots: [],
      logs: []
    });
    productionServer.executionControls.set('foreign-running', { shouldStop: false });
    const stopForeign = await request(productionServer.app)
      .post('/api/stop-execution/foreign-running');

    expect(stopForeign.status).toBe(409);
    expect(stopForeign.body.success).toBe(false);
    expect(productionServer.executionStates.get('foreign-running').status).toBe('running');
    expect(productionServer.executionControls.get('foreign-running').shouldStop).toBe(false);
    expect(productionServer.executionStates.get(activeId).status).toBe('running');
    expect(productionServer.executionControls.get(activeId).shouldStop).toBe(false);

    const activeControl = productionServer.executionControls.get(activeId);
    productionServer.executionControls.delete(activeId);
    const stopWithoutControl = await request(productionServer.app)
      .post(`/api/stop-execution/${activeId}`);

    expect(stopWithoutControl.status).toBe(409);
    expect(stopWithoutControl.body.success).toBe(false);
    expect(productionServer.executionStates.get(activeId).status).toBe('running');
    expect(activeControl.shouldStop).toBe(false);
    expect(mockBrowser.close).not.toHaveBeenCalled();

    productionServer.executionControls.set(activeId, activeControl);

    const stopActive = await request(productionServer.app)
      .post(`/api/stop-execution/${activeId}`);
    expect(stopActive.status).toBe(200);
    expect(productionServer.executionStates.get(activeId).status).toBe('stopped');
    expect(productionServer.executionControls.get(activeId).shouldStop).toBe(true);
    expect(mockBrowser.close).not.toHaveBeenCalled();
  });

  test('stop keeps admission busy until the blocked owner unwinds', async () => {
    const executionId = 'stop-holds-admission';
    await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId, testcase: testcase('https://blocked.example') });
    await waitForRunning(executionId);

    const stopped = await request(productionServer.app)
      .post(`/api/stop-execution/${executionId}`);
    expect(stopped.status).toBe(200);

    const busy = await request(productionServer.app).get('/api/status');
    const rejected = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: 'too-early', testcase: testcase('https://example.com') });
    expect(busy.body).toMatchObject({ status: 'busy', activeExecutionId: executionId });
    expect(rejected.status).toBe(409);
    expect(productionServer.executionStates.has('too-early')).toBe(false);

    releaseBlockedNavigation();
    releaseBlockedNavigation = undefined;
    await waitForReady();

    const admitted = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: 'after-owner-unwind', testcase: testcase('https://example.com') });
    expect(admitted.status).toBe(200);
    await waitForReady();
  });

  test('browser close rejection detaches damaged resources and records only the owner cleanup error', async () => {
    const secret = 'sk-cleanup-secret-value';
    const cleanupFailure = new Error(`browser close rejected ${secret}`);
    const roomEmit = jest.fn();
    const roomSpy = jest.spyOn(productionServer.io, 'to').mockReturnValue({ emit: roomEmit });
    const serverErrorLog = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockBrowser.close.mockRejectedValueOnce(cleanupFailure).mockResolvedValue(undefined);

    await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: 'cleanup-owner', testcase: testcase('https://example.com') });
    await waitForReady();

    const ownerState = productionServer.executionStates.get('cleanup-owner');
    expect(ownerState.cleanupErrors).toEqual([
      {
        resource: 'browser',
        code: 'resource_cleanup_failed',
        timestamp: expect.any(String)
      }
    ]);
    const status = await request(productionServer.app)
      .get('/api/execution-status/cleanup-owner');
    expect(status.status).toBe(200);
    expect(status.body).toEqual({
      success: true,
      executionId: 'cleanup-owner',
      status: 'success',
      progress: { currentStep: 1, totalSteps: 1 },
      steps: [{
        index: 0,
        description: 'Unknown Step',
        status: 'success',
        start_time: expect.any(String),
        end_time: expect.any(String),
        duration: expect.any(Number)
      }],
      callbackCodes: []
    });
    expect(JSON.stringify(status.body)).not.toContain(secret);
    expect(JSON.stringify(roomEmit.mock.calls)).not.toContain(secret);
    expect(JSON.stringify(serverErrorLog.mock.calls)).not.toContain(secret);
    expect(serverErrorLog).toHaveBeenCalledWith(
      expect.stringContaining('resource_cleanup_failed')
    );

    await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: 'after-cleanup-rejection', testcase: testcase('https://example.com') });
    await waitForReady();

    expect(chromium.launch).toHaveBeenCalledTimes(2);
    expect(productionServer.executionStates.get('after-cleanup-rejection').cleanupErrors).toEqual([]);
    roomSpy.mockRestore();
    serverErrorLog.mockRestore();
  });

  test('reset blocks admission, closes owned resources and waits for the active owner to unwind', async () => {
    let releaseOwner;
    const ownerResource = createAutomationResource({
      goto: jest.fn().mockImplementation(() => new Promise(resolve => {
        releaseOwner = resolve;
      }))
    });
    const nextResource = createAutomationResource();
    chromium.launch
      .mockReset()
      .mockResolvedValueOnce(ownerResource.browser)
      .mockResolvedValueOnce(nextResource.browser);

    await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: 'reset-owner', testcase: testcase('https://reset-blocked.example') });
    await waitForRunning('reset-owner');

    const resetPromise = productionServer.resetState();
    await new Promise(resolve => setImmediate(resolve));
    const duringReset = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: 'during-reset', testcase: testcase('https://example.com') });

    expect(duringReset.status).toBe(409);
    expect(ownerResource.page.close).toHaveBeenCalledTimes(1);
    expect(ownerResource.browser.close).toHaveBeenCalledTimes(1);
    expect(productionServer.executionStates.has('reset-owner')).toBe(true);

    releaseOwner();
    await resetPromise;
    expect(productionServer.executionStates.size).toBe(0);
    expect(productionServer.executionControls.size).toBe(0);

    const afterReset = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({ executionId: 'after-reset', testcase: testcase('https://example.com') });
    expect(afterReset.status).toBe(200);
    await waitForReady();
    expect(chromium.launch).toHaveBeenCalledTimes(2);
    expect(nextResource.browser.close).toHaveBeenCalledTimes(1);
  });
});
