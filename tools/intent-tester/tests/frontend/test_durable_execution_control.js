'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const controlModule = require('../../frontend/static/js/durable-execution-control.js');

function deferred() {
    let resolve;
    let reject;
    const promise = new Promise((resolvePromise, rejectPromise) => {
        resolve = resolvePromise;
        reject = rejectPromise;
    });
    return { promise, resolve, reject };
}

function response(executionId, status, options = {}) {
    return {
        status: options.httpStatus ?? 200,
        data: {
            code: options.apiCode ?? 200,
            data: {
                execution_id: executionId,
                status,
                ...(options.executionData || {})
            }
        }
    };
}

function createHarness(overrides = {}) {
    let currentExecutionId = 'run-1';
    const applied = [];
    const terminals = [];
    const waits = [];
    const httpClient = overrides.httpClient || {
        async get() {
            return response('run-1', 'running');
        },
        async post() {
            return response('run-1', 'stopped');
        }
    };
    const control = controlModule.createDurableExecutionControl({
        httpClient,
        apiBaseUrl: '/api',
        getCurrentExecutionId: () => currentExecutionId,
        applyDurableExecution: (execution) => applied.push(execution),
        onTerminal: (execution) => terminals.push(execution),
        wait: overrides.wait || (async (delayMs) => waits.push(delayMs)),
        maxReconciliationAttempts: overrides.maxReconciliationAttempts,
        reconciliationDelayMs: overrides.reconciliationDelayMs,
        continuousInitialDelayMs: overrides.continuousInitialDelayMs,
        continuousMaxDelayMs: overrides.continuousMaxDelayMs,
        continuousFailureBudget: overrides.continuousFailureBudget
    });

    return {
        applied,
        control,
        setCurrentExecutionId(value) {
            currentExecutionId = value;
        },
        terminals,
        waits
    };
}

test('completion reconciliation waits for Flask durable terminal status', async () => {
    const responses = [
        response('run-1', 'running'),
        response('run-1', 'success')
    ];
    const harness = createHarness({
        httpClient: {
            async get() {
                return responses.shift();
            }
        },
        maxReconciliationAttempts: 3,
        reconciliationDelayMs: 125
    });

    const outcome = await harness.control.refresh({ reconcileUntilTerminal: true });

    assert.equal(outcome.kind, 'terminal');
    assert.equal(outcome.attempts, 2);
    assert.deepEqual(harness.applied.map((item) => item.status), ['running', 'success']);
    assert.deepEqual(harness.terminals.map((item) => item.status), ['success']);
    assert.deepEqual(harness.waits, [125]);
});

test('reconciliation retries a request exception until Flask becomes terminal', async () => {
    let requestCount = 0;
    const responses = [
        response('run-1', 'running'),
        response('run-1', 'success')
    ];
    const harness = createHarness({
        httpClient: {
            async get() {
                requestCount += 1;
                if (requestCount === 1) {
                    throw new Error('temporary network failure');
                }
                return responses.shift();
            }
        },
        maxReconciliationAttempts: 3,
        reconciliationDelayMs: 125
    });

    const outcome = await harness.control.refresh({ reconcileUntilTerminal: true });

    assert.equal(outcome.kind, 'terminal');
    assert.equal(outcome.attempts, 3);
    assert.equal(requestCount, 3);
    assert.deepEqual(harness.waits, [125, 125]);
    assert.deepEqual(harness.applied.map((item) => item.status), ['running', 'success']);
    assert.deepEqual(harness.terminals.map((item) => item.status), ['success']);
});

test('reconciliation retries resolved HTTP and API failures until Flask becomes terminal', async (t) => {
    const cases = [
        ['HTTP 503', response('run-1', 'running', { httpStatus: 503 })],
        ['API 503', response('run-1', 'running', { apiCode: 503 })]
    ];

    for (const [name, firstResponse] of cases) {
        await t.test(name, async () => {
            let requestCount = 0;
            const responses = [
                firstResponse,
                response('run-1', 'running'),
                response('run-1', 'success')
            ];
            const harness = createHarness({
                httpClient: {
                    async get() {
                        requestCount += 1;
                        return responses.shift();
                    }
                },
                maxReconciliationAttempts: 3,
                reconciliationDelayMs: 125
            });

            const outcome = await harness.control.refresh({ reconcileUntilTerminal: true });

            assert.equal(outcome.kind, 'terminal');
            assert.equal(outcome.attempts, 3);
            assert.equal(requestCount, 3);
            assert.deepEqual(harness.waits, [125, 125]);
            assert.deepEqual(harness.applied.map((item) => item.status), ['running', 'success']);
            assert.deepEqual(harness.terminals.map((item) => item.status), ['success']);
        });
    }
});

test('an old refresh response cannot apply or complete a newer run', async () => {
    const pendingResponse = deferred();
    const harness = createHarness({
        httpClient: {
            get() {
                return pendingResponse.promise;
            }
        }
    });

    const refresh = harness.control.refresh({ reconcileUntilTerminal: true });
    harness.setCurrentExecutionId('run-2');
    pendingResponse.resolve(response('run-1', 'success'));

    const outcome = await refresh;

    assert.equal(outcome.kind, 'stale');
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
});

test('a refresh response with a mismatched execution ID is ignored', async () => {
    let requestCount = 0;
    const harness = createHarness({
        httpClient: {
            async get() {
                requestCount += 1;
                return response('run-other', 'success');
            }
        },
        maxReconciliationAttempts: 3
    });

    const outcome = await harness.control.refresh({ reconcileUntilTerminal: true });

    assert.equal(outcome.kind, 'execution_id_mismatch');
    assert.equal(outcome.attempts, 1);
    assert.equal(requestCount, 1);
    assert.deepEqual(harness.waits, []);
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
});

test('an unexpected durable status stops reconciliation immediately', async () => {
    let requestCount = 0;
    const harness = createHarness({
        httpClient: {
            async get() {
                requestCount += 1;
                return response('run-1', 'unknown');
            }
        },
        maxReconciliationAttempts: 3
    });

    const outcome = await harness.control.refresh({ reconcileUntilTerminal: true });

    assert.deepEqual(outcome, {
        kind: 'unexpected_status',
        executionId: 'run-1',
        attempts: 1,
        status: 'unknown'
    });
    assert.equal(requestCount, 1);
    assert.deepEqual(harness.waits, []);
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
});

test('healthy pending and running exhaustion is diagnosable without a failure', async (t) => {
    for (const status of ['pending', 'running']) {
        await t.test(status, async () => {
            let requestCount = 0;
            const harness = createHarness({
                httpClient: {
                    async get() {
                        requestCount += 1;
                        return response('run-1', status);
                    }
                },
                maxReconciliationAttempts: 3
            });

            const outcome = await harness.control.refresh({ reconcileUntilTerminal: true });

            assert.deepEqual(outcome, {
                kind: 'exhausted',
                executionId: 'run-1',
                attempts: 3,
                lastStatus: status
            });
            assert.equal(Object.hasOwn(outcome, 'lastFailure'), false);
            assert.equal(requestCount, 3);
            assert.equal(harness.control.isCurrentExecutionId('run-1'), true);
            assert.deepEqual(harness.terminals, []);
        });
    }
});

test('a 404 restore lookup is explicit and never applies or completes a run', async () => {
    const harness = createHarness({
        httpClient: {
            async get() {
                const error = new Error('HTTP 404');
                error.response = { status: 404 };
                throw error;
            }
        }
    });

    const outcome = await harness.control.refresh({ expectedExecutionId: 'run-1' });

    assert.deepEqual(outcome, {
        kind: 'http_failure',
        executionId: 'run-1',
        httpStatus: 404,
        attempts: 1
    });
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
    assert.equal(harness.control.isCurrentExecutionId('run-1'), true);
});

test('repeated reconciliation failures exhaust the budget with the last failure', async () => {
    let requestCount = 0;
    const harness = createHarness({
        httpClient: {
            async get() {
                requestCount += 1;
                return response('run-1', 'running', { httpStatus: 503 });
            }
        },
        maxReconciliationAttempts: 3,
        reconciliationDelayMs: 125
    });

    const outcome = await harness.control.refresh({ reconcileUntilTerminal: true });

    assert.deepEqual(outcome, {
        kind: 'exhausted',
        executionId: 'run-1',
        attempts: 3,
        lastFailure: {
            kind: 'http_failure',
            executionId: 'run-1',
            httpStatus: 503
        }
    });
    assert.equal(requestCount, 3);
    assert.deepEqual(harness.waits, [125, 125]);
    assert.equal(harness.control.isCurrentExecutionId('run-1'), true);
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
});

test('stop failures and mismatches never complete the current run', async (t) => {
    const cases = [
        ['HTTP 4xx', async () => response('run-1', 'stopped', { httpStatus: 400 }), 'http_failure'],
        ['HTTP 5xx', async () => response('run-1', 'stopped', { httpStatus: 500 }), 'http_failure'],
        ['API failure', async () => response('run-1', 'stopped', { apiCode: 503 }), 'api_failure'],
        ['ID mismatch', async () => response('run-other', 'stopped'), 'execution_id_mismatch'],
        ['request exception', async () => { throw new Error('network down'); }, 'request_failed']
    ];

    for (const [name, post, expectedKind] of cases) {
        await t.test(name, async () => {
            const harness = createHarness({ httpClient: { post } });

            const outcome = await harness.control.stop();

            assert.equal(outcome.kind, expectedKind);
            assert.equal(harness.control.isCurrentExecutionId('run-1'), true);
            assert.deepEqual(harness.applied, []);
            assert.deepEqual(harness.terminals, []);
        });
    }
});

test('a successful stop completes only the expected current run', async () => {
    const harness = createHarness();

    const outcome = await harness.control.stop();

    assert.equal(outcome.kind, 'terminal');
    assert.deepEqual(harness.applied.map((item) => item.status), ['stopped']);
    assert.deepEqual(harness.terminals.map((item) => item.status), ['stopped']);
});

test('retry posts the same canonical ID and applies only a matching active response', async (t) => {
    for (const status of ['pending', 'running']) {
        await t.test(status, async () => {
            const postUrls = [];
            const harness = createHarness({
                httpClient: {
                    async post(url) {
                        postUrls.push(url);
                        return response('run-1', status);
                    }
                }
            });

            const outcome = await harness.control.retry();

            assert.deepEqual(outcome, {
                kind: 'active',
                executionId: 'run-1',
                status
            });
            assert.deepEqual(postUrls, ['/api/executions/run-1/retry']);
            assert.deepEqual(harness.applied.map((item) => item.status), [status]);
            assert.deepEqual(harness.terminals, []);
            assert.equal(harness.control.isCurrentExecutionId('run-1'), true);
        });
    }
});

test('a deferred retry response cannot apply to a newer run', async () => {
    const pendingResponse = deferred();
    const harness = createHarness({
        httpClient: {
            post() {
                return pendingResponse.promise;
            }
        }
    });

    const retry = harness.control.retry();
    harness.setCurrentExecutionId('run-2');
    pendingResponse.resolve(response('run-1', 'running'));

    assert.deepEqual(await retry, { kind: 'stale', executionId: 'run-1' });
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
});

test('retry failures, mismatches, and terminal responses keep the current run active', async (t) => {
    const cases = [
        ['HTTP failure', async () => response('run-1', 'pending', { httpStatus: 502 }), 'http_failure'],
        ['API failure', async () => response('run-1', 'pending', { apiCode: 502 }), 'api_failure'],
        ['request exception', async () => { throw new Error('network down'); }, 'request_failed'],
        ['ID mismatch', async () => response('run-other', 'pending'), 'execution_id_mismatch'],
        ['terminal response', async () => response('run-1', 'success'), 'terminal_response']
    ];

    for (const [name, post, expectedKind] of cases) {
        await t.test(name, async () => {
            const harness = createHarness({ httpClient: { post } });

            const outcome = await harness.control.retry();

            assert.equal(outcome.kind, expectedKind);
            assert.equal(harness.control.isCurrentExecutionId('run-1'), true);
            assert.deepEqual(harness.applied, []);
            assert.deepEqual(harness.terminals, []);
        });
    }
});

test('Axios 409 and 502 retry rejections reconcile the same ID to durable terminal', async (t) => {
    for (const httpStatus of [409, 502]) {
        await t.test(`HTTP ${httpStatus}`, async () => {
            const getUrls = [];
            const harness = createHarness({
                httpClient: {
                    async post() {
                        const error = new Error(`HTTP ${httpStatus}`);
                        error.response = { status: httpStatus };
                        throw error;
                    },
                    async get(url) {
                        getUrls.push(url);
                        return response('run-1', 'success');
                    }
                }
            });

            const outcome = await harness.control.retry();

            assert.equal(outcome.kind, 'terminal');
            assert.deepEqual(getUrls, ['/api/executions/run-1']);
            assert.deepEqual(harness.applied.map((item) => item.status), ['success']);
            assert.deepEqual(harness.terminals.map((item) => item.status), ['success']);
        });
    }
});

test('retry rejection reconciliation cannot apply an old ID after the current run changes', async () => {
    const getResponse = deferred();
    let getCount = 0;
    const harness = createHarness({
        httpClient: {
            async post() {
                const error = new Error('HTTP 409');
                error.response = { status: 409 };
                throw error;
            },
            get() {
                getCount += 1;
                return getResponse.promise;
            }
        }
    });

    const retry = harness.control.retry();
    await Promise.resolve();
    harness.setCurrentExecutionId('run-2');
    getResponse.resolve(response('run-1', 'success'));

    const outcome = await retry;
    assert.equal(getCount, 1);
    assert.equal(outcome.kind, 'stale');
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
});

test('same-ID reconcile applies active durable records without completing them', async (t) => {
    for (const status of ['pending', 'running']) {
        await t.test(status, async () => {
            const postUrls = [];
            const harness = createHarness({
                httpClient: {
                    async post(url) {
                        postUrls.push(url);
                        return response('run-1', status, {
                            executionData: { result_summary: {} }
                        });
                    }
                }
            });

            const outcome = await harness.control.reconcile();

            assert.deepEqual(outcome, {
                kind: 'active',
                executionId: 'run-1',
                status
            });
            assert.deepEqual(postUrls, ['/api/executions/run-1/reconcile']);
            assert.deepEqual(harness.applied.map((item) => item.status), [status]);
            assert.deepEqual(harness.terminals, []);
        });
    }
});

test('same-ID reconcile applies and completes terminal durable records', async (t) => {
    for (const status of ['success', 'failed', 'stopped']) {
        await t.test(status, async () => {
            const harness = createHarness({
                httpClient: {
                    async post() {
                        return response('run-1', status);
                    }
                }
            });

            const outcome = await harness.control.reconcile();

            assert.deepEqual(outcome, {
                kind: 'terminal',
                executionId: 'run-1',
                status
            });
            assert.deepEqual(harness.applied.map((item) => item.status), [status]);
            assert.deepEqual(harness.terminals.map((item) => item.status), [status]);
        });
    }
});

test('a deferred reconcile response cannot apply or complete an old run', async () => {
    const reconcileResponse = deferred();
    const harness = createHarness({
        httpClient: {
            post() {
                return reconcileResponse.promise;
            }
        }
    });

    const reconcile = harness.control.reconcile();
    harness.setCurrentExecutionId('run-2');
    reconcileResponse.resolve(response('run-1', 'success'));

    assert.deepEqual(await reconcile, { kind: 'stale', executionId: 'run-1' });
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
});

test('reconcile failures, mismatches, and invalid statuses do not mutate the run', async (t) => {
    const cases = [
        ['HTTP failure', async () => response('run-1', 'running', { httpStatus: 503 }), 'http_failure'],
        ['API failure', async () => response('run-1', 'running', { apiCode: 503 }), 'api_failure'],
        ['request exception', async () => { throw new Error('network down'); }, 'request_failed'],
        ['ID mismatch', async () => response('run-other', 'running'), 'execution_id_mismatch'],
        ['invalid status', async () => response('run-1', 'unknown'), 'unexpected_status']
    ];

    for (const [name, post, expectedKind] of cases) {
        await t.test(name, async () => {
            const harness = createHarness({ httpClient: { post } });

            const outcome = await harness.control.reconcile();

            assert.equal(outcome.kind, expectedKind);
            assert.deepEqual(harness.applied, []);
            assert.deepEqual(harness.terminals, []);
            assert.equal(harness.control.isCurrentExecutionId('run-1'), true);
        });
    }
});

test('missed WebSocket polling can exhaust active then reconcile terminal on the same ID', async () => {
    const harness = createHarness({
        httpClient: {
            async get() {
                return response('run-1', 'running');
            },
            async post() {
                return response('run-1', 'success');
            }
        },
        maxReconciliationAttempts: 2
    });

    const exhausted = await harness.control.refresh({ reconcileUntilTerminal: true });
    const reconciled = await harness.control.reconcile();

    assert.equal(exhausted.kind, 'exhausted');
    assert.equal(exhausted.lastStatus, 'running');
    assert.equal(reconciled.kind, 'terminal');
    assert.deepEqual(harness.applied.map((item) => item.status), [
        'running',
        'running',
        'success'
    ]);
    assert.deepEqual(harness.terminals.map((item) => item.status), ['success']);
});

test('the current-ID predicate supports a second guard inside delayed callbacks', () => {
    const harness = createHarness();
    const expectedExecutionId = 'run-1';

    assert.equal(harness.control.isCurrentExecutionId(expectedExecutionId), true);
    harness.setCurrentExecutionId('run-2');
    assert.equal(harness.control.isCurrentExecutionId(expectedExecutionId), false);
});

test('continuous reconciliation survives the old 1.5 second window with bounded backoff', async () => {
    let requestCount = 0;
    let elapsed = 0;
    const harness = createHarness({
        httpClient: {
            async post() {
                requestCount += 1;
                return response('run-1', requestCount < 5 ? 'running' : 'success');
            }
        },
        wait: async (delayMs) => {
            harness.waits.push(delayMs);
            elapsed += delayMs;
        }
    });

    const outcome = await harness.control.startContinuousReconciliation({
        expectedExecutionId: 'run-1'
    });

    assert.equal(outcome.kind, 'terminal');
    assert.equal(requestCount, 5);
    assert.ok(elapsed > 1500);
    assert.deepEqual(harness.waits, [500, 1000, 2000, 2000]);
    assert.deepEqual(harness.terminals.map((item) => item.status), ['success']);
});

test('continuous reconciliation aborts a deferred response without applying it', async () => {
    const pending = deferred();
    let requestCount = 0;
    const controller = new AbortController();
    const harness = createHarness({
        httpClient: {
            post() {
                requestCount += 1;
                return pending.promise;
            }
        }
    });

    const running = harness.control.startContinuousReconciliation({
        expectedExecutionId: 'run-1',
        signal: controller.signal
    });
    controller.abort();
    pending.resolve(response('run-1', 'success'));

    assert.deepEqual(await running, { kind: 'cancelled', executionId: 'run-1' });
    assert.equal(requestCount, 1);
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
});

test('continuous reconciliation ignores a deferred old-ID response', async () => {
    const pending = deferred();
    const harness = createHarness({
        httpClient: { post: () => pending.promise }
    });

    const running = harness.control.startContinuousReconciliation({
        expectedExecutionId: 'run-1'
    });
    harness.setCurrentExecutionId('run-2');
    pending.resolve(response('run-1', 'success'));

    assert.deepEqual(await running, { kind: 'stale', executionId: 'run-1' });
    assert.deepEqual(harness.applied, []);
    assert.deepEqual(harness.terminals, []);
});

test('continuous reconciliation returns retry_required after its failure budget', async () => {
    let requestCount = 0;
    const harness = createHarness({
        httpClient: {
            async post() {
                requestCount += 1;
                throw new Error('network unavailable');
            }
        },
        continuousFailureBudget: 3
    });

    const outcome = await harness.control.startContinuousReconciliation({
        expectedExecutionId: 'run-1'
    });

    assert.equal(outcome.kind, 'retry_required');
    assert.equal(outcome.failures, 3);
    assert.equal(outcome.lastFailure.kind, 'request_failed');
    assert.equal(requestCount, 3);
    assert.deepEqual(harness.waits, [500, 1000]);
    assert.deepEqual(harness.terminals, []);
});

test('cancelContinuousReconciliation stops before another request', async () => {
    let requestCount = 0;
    let harness;
    harness = createHarness({
        httpClient: {
            async post() {
                requestCount += 1;
                return response('run-1', 'running');
            }
        },
        wait: async () => {
            harness.control.cancelContinuousReconciliation();
        }
    });

    const outcome = await harness.control.startContinuousReconciliation({
        expectedExecutionId: 'run-1'
    });

    assert.deepEqual(outcome, { kind: 'cancelled', executionId: 'run-1' });
    assert.equal(requestCount, 1);
});
