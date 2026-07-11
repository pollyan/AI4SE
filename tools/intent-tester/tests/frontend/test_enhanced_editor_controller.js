'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const controller = require('../../frontend/static/js/enhanced-editor-controller.js');

test('enhanced editor initializes from controller step state without table DOM', () => {
    const step = {
        action: 'aiInput',
        description: 'persisted description',
        params: { value: 'persisted value' }
    };
    const parameterForm = { kind: 'parameter-form' };
    const container = {
        children: [],
        hidden: true,
        appendChild(child) {
            this.children.push(child);
        },
        replaceChildren() {
            this.children = [];
        }
    };
    const editForm = {
        querySelector(selector) {
            assert.equal(selector, '#enhanced-params-2');
            return container;
        }
    };
    const constructorCalls = [];
    class FakeEnhancedStepEditor {
        constructor(form, index, testcaseId, executionId) {
            constructorCalls.push({ form, index, testcaseId, executionId });
        }

        createEnhancedParameterForm(receivedStep) {
            assert.equal(receivedStep, step);
            return parameterForm;
        }
    }
    const editors = new Map();
    const changes = [];

    const editor = controller.initializeEnhancedParameterEditor({
        EnhancedStepEditorClass: FakeEnhancedStepEditor,
        editForm,
        editors,
        executionId: 'run-7',
        onParameterChange(fieldName, value) {
            changes.push([fieldName, value]);
        },
        stepIndex: 2,
        steps: [{}, {}, step],
        testcaseId: 730019
    });

    assert.deepEqual(constructorCalls, [
        { form: editForm, index: 2, testcaseId: 730019, executionId: 'run-7' }
    ]);
    assert.equal(container.hidden, false);
    assert.deepEqual(container.children, [parameterForm]);
    assert.equal(editors.get(2), editor);

    editor.onParameterChange('value', 'switched value');
    assert.deepEqual(changes, [['value', 'switched value']]);
});
