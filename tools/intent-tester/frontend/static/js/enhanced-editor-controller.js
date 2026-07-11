(function (root, factory) {
    'use strict';

    const api = factory();
    if (typeof module === 'object' && module.exports) {
        module.exports = api;
    }
    if (root) {
        root.EnhancedEditorController = api;
    }
}(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function initializeEnhancedParameterEditor(options) {
        const {
            EnhancedStepEditorClass,
            editForm,
            editors,
            executionId,
            onParameterChange,
            stepIndex,
            steps,
            testcaseId
        } = options;
        const enhancedContainer = editForm.querySelector(
            `#enhanced-params-${stepIndex}`
        );
        if (!enhancedContainer) {
            throw new Error(`Enhanced parameter container missing for step ${stepIndex}`);
        }
        const step = steps[stepIndex];
        if (!step) {
            throw new Error(`Step state missing for index ${stepIndex}`);
        }

        const editor = new EnhancedStepEditorClass(
            editForm,
            stepIndex,
            testcaseId,
            executionId
        );
        const parameterForm = editor.createEnhancedParameterForm(step);
        enhancedContainer.replaceChildren();
        enhancedContainer.appendChild(parameterForm);
        enhancedContainer.hidden = false;
        editor.onParameterChange = onParameterChange;
        editors.set(stepIndex, editor);
        return editor;
    }

    return Object.freeze({ initializeEnhancedParameterEditor });
}));
