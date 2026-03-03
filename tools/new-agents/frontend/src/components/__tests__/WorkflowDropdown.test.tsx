import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorkflowDropdown } from '../WorkflowDropdown';
import { useStore, WORKFLOWS, WorkflowType } from '../../store';

describe('WorkflowDropdown Component', () => {
    beforeEach(() => {
        // Reset the store to default state
        useStore.getState().clearHistory();
        useStore.setState({ workflow: 'TEST_DESIGN' as WorkflowType });
    });

    it('renders the correct initial workflow name', () => {
        render(<WorkflowDropdown />);

        const currentWorkflowName = WORKFLOWS['TEST_DESIGN'].name;
        // There are multiple instances of the text (one in the button, one in the dropdown list)
        expect(screen.getAllByText(currentWorkflowName).length).toBeGreaterThan(0);
    });

    it('opens the dropdown when clicked', () => {
        render(<WorkflowDropdown />);

        const toggleButton = screen.getAllByText(WORKFLOWS['TEST_DESIGN'].name)[0].closest('button');
        expect(toggleButton).toBeDefined();

        fireEvent.click(toggleButton!);

        // Check if other workflow text is present in the DOM
        expect(screen.getAllByText(WORKFLOWS['REQ_REVIEW'].name).length).toBeGreaterThan(0);
    });

    it('shows a confirmation dialog when a different workflow is selected', () => {
        render(<WorkflowDropdown />);

        // Click to open
        const toggleButton = screen.getAllByText(WORKFLOWS['TEST_DESIGN'].name)[0].closest('button');
        fireEvent.click(toggleButton!);

        // Click the other workflow
        const otherWorkflowOption = screen.getAllByText(WORKFLOWS['REQ_REVIEW'].name)[0].closest('button');
        fireEvent.click(otherWorkflowOption!);

        // Confirmation dialog should appear
        expect(screen.getAllByText('切换工作流').length).toBeGreaterThan(0);
        expect(screen.getByText('确定切换')).toBeDefined();
        expect(screen.getByText('取消')).toBeDefined();
    });

    it('does not show a confirmation dialog when the current workflow is selected', () => {
        render(<WorkflowDropdown />);

        // Click to open
        const toggleButton = screen.getAllByText(WORKFLOWS['TEST_DESIGN'].name)[0].closest('button');
        fireEvent.click(toggleButton!);

        // Click the SAME workflow
        const sameWorkflowOption = screen.getAllByText(WORKFLOWS['TEST_DESIGN'].name)[1].closest('button');
        fireEvent.click(sameWorkflowOption!);

        // Confirmation dialog should NOT appear
        expect(screen.queryByText('确定切换')).toBeNull();
    });

    it('changes the workflow in the store when confirmed', () => {
        render(<WorkflowDropdown />);

        // Click to open
        const toggleButton = screen.getAllByText(WORKFLOWS['TEST_DESIGN'].name)[0].closest('button');
        fireEvent.click(toggleButton!);

        // Click the other workflow
        const otherWorkflowOption = screen.getAllByText(WORKFLOWS['REQ_REVIEW'].name)[0].closest('button');
        fireEvent.click(otherWorkflowOption!);

        // Click confirm
        const confirmButton = screen.getByText('确定切换');
        fireEvent.click(confirmButton);

        // The store workflow should be updated
        expect(useStore.getState().workflow).toBe('REQ_REVIEW');

        // Confirmation dialog should disappear
        expect(screen.queryByText('确定切换')).toBeNull();
    });

    it('cancels the workflow switch when cancel is clicked', () => {
        render(<WorkflowDropdown />);

        // Click to open
        const toggleButton = screen.getAllByText(WORKFLOWS['TEST_DESIGN'].name)[0].closest('button');
        fireEvent.click(toggleButton!);

        // Click the other workflow
        const otherWorkflowOption = screen.getAllByText(WORKFLOWS['REQ_REVIEW'].name)[0].closest('button');
        fireEvent.click(otherWorkflowOption!);

        // Click cancel
        const cancelButton = screen.getByText('取消');
        fireEvent.click(cancelButton);

        // The store workflow should NOT be updated
        expect(useStore.getState().workflow).toBe('TEST_DESIGN');

        // Confirmation dialog should disappear
        expect(screen.queryByText('确定切换')).toBeNull();
    });
});
