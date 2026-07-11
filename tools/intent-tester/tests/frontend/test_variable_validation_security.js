'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const validationSource = fs.readFileSync(
    path.resolve(__dirname, '../../frontend/static/js/utils/variableValidation.js'),
    'utf8'
);
const intentSecuritySource = fs.readFileSync(
    path.resolve(__dirname, '../../frontend/static/js/intent-security.js'),
    'utf8'
);

function validationHarness(resultCount = 1) {
    const requests = [];
    const csrfMethods = [];
    const context = {
        console,
        fetch: async (url, options) => {
            requests.push({ url, options });
            return {
                ok: true,
                async json() {
                    return {
                        validation_results: Array.from(
                            { length: resultCount },
                            () => ({ is_valid: true })
                        )
                    };
                }
            };
        },
        window: {
            API_BASE_URL: '/intent-tester/api',
            IntentSecurity: {
                csrfHeaders(method) {
                    csrfMethods.push(method);
                    return { 'X-CSRF-Token': 'review-csrf-token' };
                }
            }
        }
    };
    vm.createContext(context);
    vm.runInContext(validationSource, context);
    return { csrfMethods, requests, validation: context.window.VariableValidation };
}

test('single variable validation POST merges shared CSRF headers', async () => {
    const harness = validationHarness();

    await harness.validation.validateVariableReference('${account}', 'run-1', 0);

    assert.deepEqual(harness.csrfMethods, ['POST']);
    assert.equal(harness.requests.length, 1);
    assert.equal(harness.requests[0].options.headers['Content-Type'], 'application/json');
    assert.equal(
        harness.requests[0].options.headers['X-CSRF-Token'],
        'review-csrf-token'
    );
});

test('batch variable validation POST merges shared CSRF headers', async () => {
    const harness = validationHarness(2);

    await harness.validation.validateVariableReferences(
        ['${account}', '${profile.name}'],
        'run-1',
        1
    );

    assert.deepEqual(harness.csrfMethods, ['POST']);
    assert.equal(
        harness.requests[0].options.headers['X-CSRF-Token'],
        'review-csrf-token'
    );
});

test('IntentSecurity does not add CSRF to GET and adds it to unsafe methods', () => {
    const context = {
        document: {
            addEventListener() {},
            querySelector(selector) {
                return selector === 'meta[name="intent-csrf-token"]'
                    ? { content: 'review-csrf-token' }
                    : null;
            }
        },
        window: {}
    };
    vm.createContext(context);
    vm.runInContext(intentSecuritySource, context);

    assert.deepEqual(
        Object.fromEntries(Object.entries(context.window.IntentSecurity.csrfHeaders('GET'))),
        {}
    );
    assert.deepEqual(
        Object.fromEntries(Object.entries(context.window.IntentSecurity.csrfHeaders('PUT'))),
        { 'X-CSRF-Token': 'review-csrf-token' }
    );
});
