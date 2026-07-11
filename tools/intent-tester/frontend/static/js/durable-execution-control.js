(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.DurableExecutionControl = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const DEFAULT_RECONCILIATION_ATTEMPTS = 10;
    const DEFAULT_RECONCILIATION_DELAY_MS = 150;
    const DEFAULT_CONTINUOUS_INITIAL_DELAY_MS = 500;
    const DEFAULT_CONTINUOUS_MAX_DELAY_MS = 2000;
    const DEFAULT_CONTINUOUS_FAILURE_BUDGET = 3;
    const TERMINAL_STATUSES = ['success', 'failed', 'stopped'];
    const ACTIVE_STATUSES = ['pending', 'running'];
    const CONTINUOUS_RETRYABLE_KINDS = [
        'request_failed', 'http_failure', 'api_failure', 'wait_failed'
    ];

    function defaultWait(delayMs) {
        return new Promise((resolve) => setTimeout(resolve, delayMs));
    }

    function createDurableExecutionControl(options) {
        if (!options || !options.httpClient) {
            throw new TypeError('httpClient is required');
        }
        if (typeof options.getCurrentExecutionId !== 'function') {
            throw new TypeError('getCurrentExecutionId is required');
        }
        if (typeof options.applyDurableExecution !== 'function') {
            throw new TypeError('applyDurableExecution is required');
        }
        if (typeof options.onTerminal !== 'function') {
            throw new TypeError('onTerminal is required');
        }

        const httpClient = options.httpClient;
        const apiBaseUrl = (options.apiBaseUrl || '').replace(/\/$/, '');
        const getCurrentExecutionId = options.getCurrentExecutionId;
        const applyDurableExecution = options.applyDurableExecution;
        const onTerminal = options.onTerminal;
        const wait = options.wait || defaultWait;
        const maxReconciliationAttempts = Number.isInteger(options.maxReconciliationAttempts)
            ? options.maxReconciliationAttempts
            : DEFAULT_RECONCILIATION_ATTEMPTS;
        const reconciliationDelayMs = Number.isFinite(options.reconciliationDelayMs)
            ? options.reconciliationDelayMs
            : DEFAULT_RECONCILIATION_DELAY_MS;
        const continuousInitialDelayMs = Number.isFinite(options.continuousInitialDelayMs)
            ? options.continuousInitialDelayMs
            : DEFAULT_CONTINUOUS_INITIAL_DELAY_MS;
        const continuousMaxDelayMs = Number.isFinite(options.continuousMaxDelayMs)
            ? options.continuousMaxDelayMs
            : DEFAULT_CONTINUOUS_MAX_DELAY_MS;
        const continuousFailureBudget = Number.isInteger(options.continuousFailureBudget)
            ? options.continuousFailureBudget
            : DEFAULT_CONTINUOUS_FAILURE_BUDGET;
        let continuousGeneration = 0;

        if (maxReconciliationAttempts < 1) {
            throw new RangeError('maxReconciliationAttempts must be at least 1');
        }
        if (reconciliationDelayMs < 0) {
            throw new RangeError('reconciliationDelayMs must not be negative');
        }
        if (continuousInitialDelayMs < 0) {
            throw new RangeError('continuousInitialDelayMs must not be negative');
        }
        if (continuousMaxDelayMs < continuousInitialDelayMs) {
            throw new RangeError('continuousMaxDelayMs must be at least continuousInitialDelayMs');
        }
        if (continuousFailureBudget < 1) {
            throw new RangeError('continuousFailureBudget must be at least 1');
        }

        function isCurrentExecutionId(expectedExecutionId) {
            return Boolean(
                expectedExecutionId &&
                getCurrentExecutionId() === expectedExecutionId
            );
        }

        function executionUrl(executionId, suffix) {
            return `${apiBaseUrl}/executions/${encodeURIComponent(executionId)}${suffix || ''}`;
        }

        function validateResponse(response, expectedExecutionId) {
            if (!response || response.status !== 200) {
                return {
                    kind: 'http_failure',
                    executionId: expectedExecutionId,
                    httpStatus: response && response.status
                };
            }
            if (!response.data || response.data.code !== 200) {
                return {
                    kind: 'api_failure',
                    executionId: expectedExecutionId,
                    apiCode: response.data && response.data.code
                };
            }

            const execution = response.data.data;
            if (!execution || execution.execution_id !== expectedExecutionId) {
                return {
                    kind: 'execution_id_mismatch',
                    executionId: expectedExecutionId,
                    responseExecutionId: execution && execution.execution_id
                };
            }
            return { execution };
        }

        async function refresh(refreshOptions) {
            const requestedExecutionId = (
                refreshOptions && refreshOptions.expectedExecutionId
            ) || getCurrentExecutionId();
            const reconcileUntilTerminal = Boolean(
                refreshOptions && refreshOptions.reconcileUntilTerminal
            );
            const attemptsBudget = reconcileUntilTerminal ? maxReconciliationAttempts : 1;

            if (!requestedExecutionId) {
                return { kind: 'no_current_execution' };
            }

            let lastStatus;
            let lastFailure;
            for (let attempt = 1; attempt <= attemptsBudget; attempt += 1) {
                if (!isCurrentExecutionId(requestedExecutionId)) {
                    return {
                        kind: 'stale',
                        executionId: requestedExecutionId,
                        attempts: attempt - 1
                    };
                }

                let response;
                let transientFailure;
                try {
                    response = await httpClient.get(executionUrl(requestedExecutionId));
                } catch (error) {
                    const httpStatus = error && error.response && error.response.status;
                    transientFailure = httpStatus === undefined
                        ? {
                            kind: 'request_failed',
                            executionId: requestedExecutionId,
                            error
                        }
                        : {
                            kind: 'http_failure',
                            executionId: requestedExecutionId,
                            httpStatus
                        };
                }

                if (!isCurrentExecutionId(requestedExecutionId)) {
                    return {
                        kind: 'stale',
                        executionId: requestedExecutionId,
                        attempts: attempt
                    };
                }

                if (!transientFailure) {
                    const validated = validateResponse(response, requestedExecutionId);
                    if (!validated.execution) {
                        if (
                            !reconcileUntilTerminal ||
                            validated.kind === 'execution_id_mismatch'
                        ) {
                            return { ...validated, attempts: attempt };
                        }
                        transientFailure = validated;
                    } else {
                        const durableExecution = validated.execution;
                        lastFailure = undefined;
                        lastStatus = durableExecution.status;
                        if (
                            !ACTIVE_STATUSES.includes(lastStatus) &&
                            !TERMINAL_STATUSES.includes(lastStatus)
                        ) {
                            return {
                                kind: 'unexpected_status',
                                executionId: requestedExecutionId,
                                attempts: attempt,
                                status: lastStatus
                            };
                        }

                        applyDurableExecution(durableExecution, requestedExecutionId);

                        if (TERMINAL_STATUSES.includes(lastStatus)) {
                            if (!isCurrentExecutionId(requestedExecutionId)) {
                                return {
                                    kind: 'stale',
                                    executionId: requestedExecutionId,
                                    attempts: attempt
                                };
                            }
                            onTerminal(durableExecution, requestedExecutionId);
                            return {
                                kind: 'terminal',
                                executionId: requestedExecutionId,
                                attempts: attempt,
                                status: lastStatus
                            };
                        }

                        if (!reconcileUntilTerminal) {
                            return {
                                kind: 'active',
                                executionId: requestedExecutionId,
                                attempts: attempt,
                                status: lastStatus
                            };
                        }
                    }
                }

                if (transientFailure) {
                    lastFailure = transientFailure;
                    if (!reconcileUntilTerminal) {
                        return {
                            ...transientFailure,
                            attempts: attempt
                        };
                    }
                }

                if (attempt < attemptsBudget) {
                    try {
                        await wait(reconciliationDelayMs);
                    } catch (error) {
                        return {
                            kind: 'wait_failed',
                            executionId: requestedExecutionId,
                            attempts: attempt,
                            error
                        };
                    }
                }
            }

            return {
                kind: 'exhausted',
                executionId: requestedExecutionId,
                attempts: attemptsBudget,
                ...(lastStatus === undefined ? {} : { lastStatus }),
                ...(lastFailure === undefined ? {} : { lastFailure })
            };
        }

        async function stop() {
            const requestedExecutionId = getCurrentExecutionId();
            if (!requestedExecutionId) {
                return { kind: 'no_current_execution' };
            }
            if (!isCurrentExecutionId(requestedExecutionId)) {
                return { kind: 'stale', executionId: requestedExecutionId };
            }

            let response;
            try {
                response = await httpClient.post(executionUrl(requestedExecutionId, '/stop'));
            } catch (error) {
                return { kind: 'request_failed', executionId: requestedExecutionId, error };
            }

            if (!isCurrentExecutionId(requestedExecutionId)) {
                return { kind: 'stale', executionId: requestedExecutionId };
            }

            const validated = validateResponse(response, requestedExecutionId);
            if (!validated.execution) {
                return validated;
            }

            const durableExecution = validated.execution;
            if (!TERMINAL_STATUSES.includes(durableExecution.status)) {
                return {
                    kind: 'unexpected_status',
                    executionId: requestedExecutionId,
                    status: durableExecution.status
                };
            }

            applyDurableExecution(durableExecution, requestedExecutionId);
            if (!isCurrentExecutionId(requestedExecutionId)) {
                return { kind: 'stale', executionId: requestedExecutionId };
            }
            onTerminal(durableExecution, requestedExecutionId);
            return {
                kind: 'terminal',
                executionId: requestedExecutionId,
                status: durableExecution.status
            };
        }

        async function retry() {
            const requestedExecutionId = getCurrentExecutionId();
            if (!requestedExecutionId) {
                return { kind: 'no_current_execution' };
            }
            if (!isCurrentExecutionId(requestedExecutionId)) {
                return { kind: 'stale', executionId: requestedExecutionId };
            }

            let response;
            try {
                response = await httpClient.post(executionUrl(requestedExecutionId, '/retry'));
            } catch (error) {
                const retryHttpStatus = error && error.response && error.response.status;
                if (retryHttpStatus === 409 || retryHttpStatus === 502) {
                    const reconciliation = await refresh({
                        expectedExecutionId: requestedExecutionId
                    });
                    if (
                        reconciliation.kind === 'terminal' ||
                        reconciliation.kind === 'stale'
                    ) {
                        return reconciliation;
                    }
                    return {
                        kind: 'retry_rejected',
                        executionId: requestedExecutionId,
                        httpStatus: retryHttpStatus,
                        reconciliation
                    };
                }
                return { kind: 'request_failed', executionId: requestedExecutionId, error };
            }

            if (!isCurrentExecutionId(requestedExecutionId)) {
                return { kind: 'stale', executionId: requestedExecutionId };
            }

            const validated = validateResponse(response, requestedExecutionId);
            if (!validated.execution) {
                return validated;
            }

            const durableExecution = validated.execution;
            if (TERMINAL_STATUSES.includes(durableExecution.status)) {
                return {
                    kind: 'terminal_response',
                    executionId: requestedExecutionId,
                    status: durableExecution.status
                };
            }
            if (!ACTIVE_STATUSES.includes(durableExecution.status)) {
                return {
                    kind: 'unexpected_status',
                    executionId: requestedExecutionId,
                    status: durableExecution.status
                };
            }

            applyDurableExecution(durableExecution, requestedExecutionId);
            if (!isCurrentExecutionId(requestedExecutionId)) {
                return { kind: 'stale', executionId: requestedExecutionId };
            }
            return {
                kind: 'active',
                executionId: requestedExecutionId,
                status: durableExecution.status
            };
        }

        async function reconcile(reconcileOptions) {
            const requestedExecutionId = (
                reconcileOptions && reconcileOptions.expectedExecutionId
            ) || getCurrentExecutionId();
            const shouldApply = reconcileOptions && reconcileOptions.shouldApply;
            if (!requestedExecutionId) {
                return { kind: 'no_current_execution' };
            }
            if (
                !isCurrentExecutionId(requestedExecutionId) ||
                (typeof shouldApply === 'function' && !shouldApply())
            ) {
                return { kind: 'stale', executionId: requestedExecutionId };
            }

            let response;
            try {
                response = await httpClient.post(
                    executionUrl(requestedExecutionId, '/reconcile')
                );
            } catch (error) {
                const httpStatus = error && error.response && error.response.status;
                if (httpStatus !== undefined) {
                    return {
                        kind: 'http_failure',
                        executionId: requestedExecutionId,
                        httpStatus
                    };
                }
                return {
                    kind: 'request_failed',
                    executionId: requestedExecutionId,
                    error
                };
            }

            if (
                !isCurrentExecutionId(requestedExecutionId) ||
                (typeof shouldApply === 'function' && !shouldApply())
            ) {
                return { kind: 'stale', executionId: requestedExecutionId };
            }

            const validated = validateResponse(response, requestedExecutionId);
            if (!validated.execution) {
                return validated;
            }

            const durableExecution = validated.execution;
            const status = durableExecution.status;
            if (!ACTIVE_STATUSES.includes(status) && !TERMINAL_STATUSES.includes(status)) {
                return {
                    kind: 'unexpected_status',
                    executionId: requestedExecutionId,
                    status
                };
            }

            applyDurableExecution(durableExecution, requestedExecutionId);
            if (
                !isCurrentExecutionId(requestedExecutionId) ||
                (typeof shouldApply === 'function' && !shouldApply())
            ) {
                return { kind: 'stale', executionId: requestedExecutionId };
            }

            if (TERMINAL_STATUSES.includes(status)) {
                onTerminal(durableExecution, requestedExecutionId);
                return {
                    kind: 'terminal',
                    executionId: requestedExecutionId,
                    status
                };
            }
            return {
                kind: 'active',
                executionId: requestedExecutionId,
                status
            };
        }

        function cancelContinuousReconciliation() {
            continuousGeneration += 1;
        }

        async function startContinuousReconciliation(continuousOptions) {
            const requestedExecutionId = (
                continuousOptions && continuousOptions.expectedExecutionId
            ) || getCurrentExecutionId();
            const signal = continuousOptions && continuousOptions.signal;
            if (!requestedExecutionId) {
                return { kind: 'no_current_execution' };
            }

            const generation = continuousGeneration + 1;
            continuousGeneration = generation;
            const cancellationOutcome = () => {
                if (!isCurrentExecutionId(requestedExecutionId)) {
                    return { kind: 'stale', executionId: requestedExecutionId };
                }
                if ((signal && signal.aborted) || generation !== continuousGeneration) {
                    return { kind: 'cancelled', executionId: requestedExecutionId };
                }
                return null;
            };
            const shouldApply = () => cancellationOutcome() === null;

            let delayMs = continuousInitialDelayMs;
            let failures = 0;
            let attempts = 0;
            while (true) {
                const beforeRequest = cancellationOutcome();
                if (beforeRequest) return beforeRequest;

                const outcome = await reconcile({
                    expectedExecutionId: requestedExecutionId,
                    shouldApply
                });
                const afterRequest = cancellationOutcome();
                if (afterRequest) return afterRequest;
                attempts += 1;

                if (outcome.kind === 'terminal') {
                    return { ...outcome, attempts };
                }
                if (outcome.kind === 'active') {
                    failures = 0;
                } else if (CONTINUOUS_RETRYABLE_KINDS.includes(outcome.kind)) {
                    failures += 1;
                    if (failures >= continuousFailureBudget) {
                        return {
                            kind: 'retry_required',
                            executionId: requestedExecutionId,
                            attempts,
                            failures,
                            lastFailure: outcome
                        };
                    }
                } else {
                    return outcome;
                }

                try {
                    await wait(delayMs);
                } catch (error) {
                    failures += 1;
                    if (failures >= continuousFailureBudget) {
                        return {
                            kind: 'retry_required',
                            executionId: requestedExecutionId,
                            attempts,
                            failures,
                            lastFailure: {
                                kind: 'wait_failed',
                                executionId: requestedExecutionId,
                                error
                            }
                        };
                    }
                }
                const afterWait = cancellationOutcome();
                if (afterWait) return afterWait;
                delayMs = Math.min(continuousMaxDelayMs, delayMs * 2);
            }
        }

        return {
            cancelContinuousReconciliation,
            isCurrentExecutionId,
            reconcile,
            refresh,
            retry,
            startContinuousReconciliation,
            stop
        };
    }

    return {
        ACTIVE_STATUSES,
        DEFAULT_CONTINUOUS_FAILURE_BUDGET,
        DEFAULT_CONTINUOUS_INITIAL_DELAY_MS,
        DEFAULT_CONTINUOUS_MAX_DELAY_MS,
        DEFAULT_RECONCILIATION_ATTEMPTS,
        DEFAULT_RECONCILIATION_DELAY_MS,
        TERMINAL_STATUSES,
        createDurableExecutionControl
    };
}));
