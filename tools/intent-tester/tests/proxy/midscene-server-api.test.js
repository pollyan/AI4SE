/** Production HTTP API contract tests for the MidScene Node server. */

const request = require('supertest');

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
    const status = await request(productionServer.app).get('/api/status');
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
    const websocketEmit = jest.spyOn(productionServer.io, 'emit');
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
    expect(status.body.cleanupErrors).toEqual(ownerState.cleanupErrors);
    expect(JSON.stringify(status.body)).not.toContain(secret);
    expect(JSON.stringify(websocketEmit.mock.calls)).not.toContain(secret);
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
    websocketEmit.mockRestore();
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
