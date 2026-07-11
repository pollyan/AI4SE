/**
 * Production MidScene server integration contract.
 *
 * The Express app is loaded directly. Only external automation, WebSocket and
 * lifecycle HTTP adapters are replaced at their boundaries.
 */

const rawRequest = require('supertest');
const { spawnSync } = require('child_process');
const crypto = require('crypto');
const path = require('path');
const { io: createSocketClient } = require('socket.io-client');

const CANARY_TOKEN = 'qs04-canary-proxy-token-0123456789abcdef';
const PUBLIC_ORIGIN = 'http://127.0.0.1:5001';
const bearer = `Bearer ${CANARY_TOKEN}`;
const openSocketClients = new Set();
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
process.env.MAIN_APP_URL = 'http://flask.example/intent-tester/api';
process.env.NODE_ENV = 'test';
process.env.INTENT_PROXY_TOPOLOGY = 'local-host';
process.env.INTENT_PROXY_TOKEN = CANARY_TOKEN;
process.env.INTENT_PUBLIC_ORIGIN = PUBLIC_ORIGIN;

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
    const status = await request(productionServer.app).get('/api/status').set('Authorization', bearer);
    if (status.body.status === 'ready') {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  throw new Error('Production execution runtime did not become ready');
}

function base64url(value) {
  return Buffer.from(value).toString('base64url');
}

function socketTicket(executionId, overrides = {}) {
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    executionId,
    origin: PUBLIC_ORIGIN,
    aud: 'intent-proxy-socket',
    iat: now,
    exp: now + 60,
    nonce: `nonce-${executionId}`,
    ...overrides
  };
  const encoded = base64url(JSON.stringify(payload));
  const signature = crypto.createHmac('sha256', CANARY_TOKEN).update(Buffer.from(encoded, 'base64url')).digest('base64url');
  return `${encoded}.${signature}`;
}

function connectSocket(url, ticket, executionId) {
  const client = createSocketClient(url, {
    transports: ['websocket'],
    forceNew: true,
    reconnection: false,
    auth: { ticket, executionId },
    extraHeaders: { Origin: PUBLIC_ORIGIN }
  });
  openSocketClients.add(client);
  client.on('disconnect', () => openSocketClients.delete(client));
  return client;
}

function once(socket, event) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`timed out waiting for ${event}`)), 2000);
    socket.once(event, value => { clearTimeout(timer); resolve(value); });
  });
}

describe('MidScene production server integration contract', () => {
  beforeEach(async () => {
    await productionServer.resetState();
    mockHttpClient.post.mockReset().mockResolvedValue({ status: 200, data: {} });
    productionServer.setLifecycleHttpClient(mockHttpClient);
  });

  afterEach(async () => {
    for (const client of openSocketClients) client.close();
    openSocketClients.clear();
    productionServer.setRuntimeConfigForTest?.(productionServer.loadRuntimeConfig?.(process.env));
    if (productionServer.server.listening) await productionServer.closeServer();
  });

  afterAll(async () => {
    await productionServer.closeServer();
  });

  test('requiring the production module does not listen and exposes its real app', async () => {
    expect(productionServer.server.listening).toBe(false);

    const response = await rawRequest(productionServer.app).get('/health');

    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
  });

  test('real Socket.IO clients authenticate tickets, receive only their snapshot and room events', async () => {
    await new Promise(resolve => productionServer.server.listen(0, '127.0.0.1', resolve));
    const address = productionServer.server.address();
    const url = `http://127.0.0.1:${address.port}`;
    productionServer.executionStates.set('execution-a', {
      id: 'execution-a', status: 'running', currentStep: 1, totalSteps: 3,
      steps: [{
        index: 0, description: 'Safe step', status: 'success',
        start_time: '2026-07-11T01:00:00.000Z',
        end_time: '2026-07-11T01:00:01.000Z', duration: 1000,
        params: { token: CANARY_TOKEN }, error_message: CANARY_TOKEN
      }],
      logs: [CANARY_TOKEN], screenshots: ['/private/a.png']
    });
    productionServer.executionStates.set('execution-b', { id: 'execution-b', status: 'running' });

    const clientA = connectSocket(url, socketTicket('execution-a'), 'execution-a');
    const clientB = connectSocket(url, socketTicket('execution-b'), 'execution-b');
    const snapshotA = await once(clientA, 'execution-snapshot');
    await once(clientB, 'connect');
    expect(snapshotA).toEqual({
      executionId: 'execution-a', status: 'running',
      progress: { currentStep: 1, totalSteps: 3 },
      steps: [{
        index: 0, description: 'Safe step', status: 'success',
        start_time: '2026-07-11T01:00:00.000Z',
        end_time: '2026-07-11T01:00:01.000Z', duration: 1000
      }],
      callbackCodes: []
    });
    expect(JSON.stringify(snapshotA)).not.toContain(CANARY_TOKEN);

    const receivedA = [];
    const receivedB = [];
    clientA.on('execution-progress', value => receivedA.push(value));
    clientB.on('execution-progress', value => receivedB.push(value));
    productionServer.emitExecutionEvent('execution-a', 'execution-progress', {
      executionId: 'execution-a', progress: { currentStep: 2, totalSteps: 3 }
    });
    await new Promise(resolve => setTimeout(resolve, 50));
    expect(receivedA).toHaveLength(1);
    expect(receivedB).toHaveLength(0);
    clientA.close();
    clientB.close();
    await productionServer.closeServer();
  });

  test.each([
    ['tampered signature', `${socketTicket('ticket-id')}x`, 'ticket-id'],
    ['expired', socketTicket('ticket-id', { iat: 1, exp: 2 }), 'ticket-id'],
    ['wrong audience', socketTicket('ticket-id', { aud: 'other' }), 'ticket-id'],
    ['wrong origin', socketTicket('ticket-id', { origin: 'http://foreign.example' }), 'ticket-id'],
    ['missing signed execution ID', socketTicket('ticket-id', { executionId: '' }), 'ticket-id'],
    ['requested execution mismatch', socketTicket('ticket-id'), 'other-id']
  ])('Socket.IO rejects %s without leaking the token', async (_label, ticket, executionId) => {
    if (!productionServer.server.listening) {
      await new Promise(resolve => productionServer.server.listen(0, '127.0.0.1', resolve));
    }
    const address = productionServer.server.address();
    const client = connectSocket(`http://127.0.0.1:${address.port}`, ticket, executionId);
    const error = await once(client, 'connect_error');
    expect(error.message).toBe('SOCKET_TICKET_INVALID');
    expect(String(error.message)).not.toContain(CANARY_TOKEN);
    client.close();
  });

  test('managed topology rejects browser Socket with stable code', async () => {
    productionServer.setRuntimeConfigForTest(productionServer.loadRuntimeConfig({
      INTENT_PROXY_TOPOLOGY: 'managed',
      INTENT_PROXY_TOKEN: CANARY_TOKEN,
      INTENT_PUBLIC_ORIGIN: PUBLIC_ORIGIN
    }));
    if (!productionServer.server.listening) {
      await new Promise(resolve => productionServer.server.listen(0, '127.0.0.1', resolve));
    }
    const address = productionServer.server.address();
    const client = connectSocket(`http://127.0.0.1:${address.port}`, socketTicket('managed-id'), 'managed-id');
    const error = await once(client, 'connect_error');
    expect(error.message).toBe('BROWSER_SOCKET_DISABLED');
    client.close();
    productionServer.setRuntimeConfigForTest(productionServer.loadRuntimeConfig(process.env));
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

  test.each(['OPENAI_BASE_URL', 'MIDSCENE_MODEL_NAME', 'MAIN_APP_URL'])(
    'production entrypoint fails closed when %s is missing',
    variableName => {
      const child = spawnSync(process.execPath, [productionServerPath], {
        cwd: path.dirname(productionServerPath),
        env: { ...process.env, [variableName]: '' },
        encoding: 'utf8',
        timeout: 5000
      });
      expect(child.status).toBe(1);
      expect(child.stderr).toContain(`Missing required environment variables: ${variableName}`);
      expect(`${child.stdout}${child.stderr}`).not.toContain(CANARY_TOKEN);
    }
  );

  test('caller executionId is reused by response, state, websocket path and lifecycle callbacks', async () => {
    const executionId = 'canonical-execution-123';
    const roomEmit = jest.fn();
    const roomSpy = jest.spyOn(productionServer.io, 'to').mockReturnValue({ emit: roomEmit });

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
    const executionEvents = roomEmit.mock.calls.filter(([event]) =>
      ['execution-start', 'execution-completed'].includes(event)
    );
    expect(executionEvents.length).toBeGreaterThan(0);
    expect(executionEvents.every(([, payload]) => payload.executionId === executionId)).toBe(true);
    expect(roomSpy.mock.calls.every(([room]) => room === `execution:${executionId}`)).toBe(true);

    const lifecycleCalls = mockHttpClient.post.mock.calls.filter(([url]) =>
      url.includes(`/executions/${executionId}/lifecycle`)
    );
    expect(lifecycleCalls).toHaveLength(2);
    expect(lifecycleCalls.every(([url]) =>
      url === `http://flask.example/intent-tester/api/executions/${executionId}/lifecycle`
    )).toBe(true);
    expect(lifecycleCalls[0][1]).toMatchObject({ event: 'started', status: 'running' });
    expect(lifecycleCalls[1][1]).toMatchObject({ event: 'result', status: 'success' });
    expect(state.callbackErrors).toEqual([]);
    roomSpy.mockRestore();
  });

  test('lifecycle callback retries only failures and transient success leaves no canonical error', async () => {
    const executionId = 'callback-transient-success';
    const roomEmit = jest.fn();
    const roomSpy = jest.spyOn(productionServer.io, 'to').mockReturnValue({ emit: roomEmit });
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
    expect(roomEmit.mock.calls.filter(([event]) =>
      event === 'lifecycle-callback-failed'
    )).toEqual([]);
    roomSpy.mockRestore();
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
    const roomEmit = jest.fn();
    const roomSpy = jest.spyOn(productionServer.io, 'to').mockReturnValue({ emit: roomEmit });

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
    const failedEvents = roomEmit.mock.calls
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
    expect(JSON.stringify(roomEmit.mock.calls)).not.toContain(secret);
    roomSpy.mockRestore();
  });
});
