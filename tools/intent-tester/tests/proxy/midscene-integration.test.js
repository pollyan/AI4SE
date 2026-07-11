/**
 * Production MidScene server integration contract.
 *
 * The Express app is loaded directly. Only external automation, WebSocket and
 * lifecycle HTTP adapters are replaced at their boundaries.
 */

const request = require('supertest');
const { spawnSync } = require('child_process');
const path = require('path');

const mockHttpClient = {
  post: jest.fn().mockResolvedValue({ status: 200, data: {} })
};

const mockPage = {
  setDefaultTimeout: jest.fn(),
  setDefaultNavigationTimeout: jest.fn(),
  goto: jest.fn().mockResolvedValue(undefined),
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

jest.mock('@midscene/web', () => ({
  PlaywrightAgent: jest.fn().mockImplementation(() => ({}))
}));
jest.mock('playwright', () => ({
  chromium: { launch: jest.fn().mockResolvedValue(mockBrowser) }
}));
process.env.OPENAI_API_KEY = 'test-api-key';
process.env.OPENAI_BASE_URL = 'https://test-api.example/v1';
process.env.MIDSCENE_MODEL_NAME = 'test-model';
delete process.env.MAIN_APP_URL;
process.env.NODE_ENV = 'test';

const productionServer = require('../../browser-automation/midscene_server');
const productionServerPath = path.resolve(__dirname, '../../browser-automation/midscene_server.js');

async function waitForTerminalState(executionId) {
  const deadline = Date.now() + 3000;
  while (Date.now() < deadline) {
    const state = productionServer.executionStates.get(executionId);
    if (state && state.status !== 'running') {
      return state;
    }
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  throw new Error(`Execution ${executionId} did not reach a terminal state`);
}

async function waitForReady() {
  const deadline = Date.now() + 3000;
  while (Date.now() < deadline) {
    const status = await request(productionServer.app).get('/api/status');
    if (status.body.status === 'ready') {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  throw new Error('Production execution runtime did not become ready');
}

describe('MidScene production server integration contract', () => {
  beforeEach(async () => {
    await productionServer.resetState();
    mockHttpClient.post.mockReset().mockResolvedValue({ status: 200, data: {} });
    productionServer.setLifecycleHttpClient(mockHttpClient);
  });

  afterAll(async () => {
    await productionServer.closeServer();
  });

  test('requiring the production module does not listen and exposes its real app', async () => {
    expect(productionServer.server.listening).toBe(false);

    const response = await request(productionServer.app).get('/health');

    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
  });

  test('requiring the production module does not validate missing startup environment', () => {
    const script = `delete process.env.OPENAI_API_KEY; const service = require(${JSON.stringify(productionServerPath)}); process.stdout.write(String(service.server.listening));`;
    const child = spawnSync(process.execPath, ['-e', script], {
      cwd: path.dirname(productionServerPath),
      env: { ...process.env, OPENAI_API_KEY: '' },
      encoding: 'utf8',
      timeout: 5000
    });

    expect(child.status).toBe(0);
    expect(child.stdout).toContain('false');
  });

  test('running the production entrypoint still validates startup environment', () => {
    const child = spawnSync(process.execPath, [productionServerPath], {
      cwd: path.dirname(productionServerPath),
      env: { ...process.env, OPENAI_API_KEY: '' },
      encoding: 'utf8',
      timeout: 5000
    });

    expect(child.status).toBe(1);
    expect(child.stderr).toContain('Missing required environment variables: OPENAI_API_KEY');
  });

  test('caller executionId is reused by response, state, websocket path and lifecycle callbacks', async () => {
    const executionId = 'canonical-execution-123';
    const websocketEmit = jest.spyOn(productionServer.io, 'emit');

    const response = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({
        executionId,
        testcase: {
          id: 7,
          name: 'Canonical ID contract',
          steps: [{ type: 'navigate', params: { url: 'https://example.com' } }]
        },
        mode: 'headless'
      });

    expect(response.status).toBe(200);
    expect(response.body.executionId).toBe(executionId);
    const state = await waitForTerminalState(executionId);
    expect(state.id).toBe(executionId);
    expect(productionServer.executionStates.has(executionId)).toBe(true);
    const executionEvents = websocketEmit.mock.calls.filter(([event]) =>
      ['execution-start', 'execution-completed'].includes(event)
    );
    expect(executionEvents.length).toBeGreaterThan(0);
    expect(executionEvents.every(([, payload]) => payload.executionId === executionId)).toBe(true);

    const lifecycleCalls = mockHttpClient.post.mock.calls.filter(([url]) =>
      url.includes(`/executions/${executionId}/lifecycle`)
    );
    expect(lifecycleCalls).toHaveLength(2);
    expect(lifecycleCalls.every(([url]) =>
      url === `http://localhost:5001/intent-tester/api/executions/${executionId}/lifecycle`
    )).toBe(true);
    expect(lifecycleCalls[0][1]).toMatchObject({ event: 'started', status: 'running' });
    expect(lifecycleCalls[1][1]).toMatchObject({ event: 'result', status: 'success' });
    expect(state.callbackErrors).toEqual([]);
    websocketEmit.mockRestore();
  });

  test('lifecycle callback retries only failures and transient success leaves no canonical error', async () => {
    const executionId = 'callback-transient-success';
    const websocketEmit = jest.spyOn(productionServer.io, 'emit');
    mockHttpClient.post
      .mockRejectedValueOnce(new Error('temporary transport failure'))
      .mockResolvedValueOnce({ status: 503, statusText: 'temporarily unavailable' })
      .mockResolvedValueOnce({ status: 204, data: {} })
      .mockResolvedValueOnce({ status: 200, data: {} });

    const response = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({
        executionId,
        testcase: {
          id: 8,
          name: 'Callback transient success',
          steps: [{ type: 'navigate', params: { url: 'https://example.com' } }]
        }
      });

    expect(response.status).toBe(200);
    const canonicalState = productionServer.executionStates.get(executionId);
    await waitForTerminalState(executionId);
    await waitForReady();

    const lifecycleCalls = mockHttpClient.post.mock.calls.filter(([url]) =>
      url.includes(`/executions/${executionId}/lifecycle`)
    );
    expect(lifecycleCalls).toHaveLength(4);
    expect(lifecycleCalls.filter(([, body]) => body.event === 'started')).toHaveLength(3);
    expect(lifecycleCalls.filter(([, body]) => body.event === 'result')).toHaveLength(1);
    expect(canonicalState.callbackErrors).toEqual([]);
    expect(websocketEmit.mock.calls.filter(([event]) =>
      event === 'lifecycle-callback-failed'
    )).toEqual([]);
    websocketEmit.mockRestore();
  });

  test('exhausted lifecycle callbacks persist and emit only the sanitized canonical contract', async () => {
    const executionId = 'callback-failure-visible';
    const secret = 'sk-secret-upstream-message';
    const attemptsByEvent = { started: 0, result: 0 };
    mockHttpClient.post.mockImplementation(async (_url, body) => {
      attemptsByEvent[body.event] += 1;
      if (body.event === 'started') {
        throw new Error(`Flask lifecycle unavailable ${secret}`);
      }
      return { status: 503, statusText: `do not broadcast ${secret}` };
    });
    const websocketEmit = jest.spyOn(productionServer.io, 'emit');

    const response = await request(productionServer.app)
      .post('/api/execute-testcase')
      .send({
        executionId,
        testcase: {
          id: 8,
          name: 'Callback failure',
          steps: [{ type: 'navigate', params: { url: 'https://example.com' } }]
        }
      });

    expect(response.status).toBe(200);
    const canonicalState = productionServer.executionStates.get(executionId);
    await waitForTerminalState(executionId);
    await waitForReady();

    expect(productionServer.executionStates.get(executionId)).toBe(canonicalState);
    expect(attemptsByEvent).toEqual({ started: 3, result: 3 });
    expect(canonicalState.callbackErrors).toEqual([
      {
        event: 'started',
        code: 'lifecycle_callback_exhausted',
        attempts: 3,
        timestamp: expect.any(String)
      },
      {
        event: 'result',
        code: 'lifecycle_callback_exhausted',
        attempts: 3,
        timestamp: expect.any(String)
      }
    ]);
    const failedEvents = websocketEmit.mock.calls
      .filter(([event]) => event === 'lifecycle-callback-failed')
      .map(([, payload]) => payload);
    expect(failedEvents).toEqual([
      {
        executionId,
        event: 'started',
        code: 'lifecycle_callback_exhausted',
        attempts: 3
      },
      {
        executionId,
        event: 'result',
        code: 'lifecycle_callback_exhausted',
        attempts: 3
      }
    ]);
    expect(JSON.stringify(canonicalState.callbackErrors)).not.toContain(secret);
    expect(JSON.stringify(websocketEmit.mock.calls)).not.toContain(secret);
    websocketEmit.mockRestore();
  });
});
