import { render, screen } from '@testing-library/react';
import React from 'react';
import { DiffField } from '../DiffField';
import '@testing-library/jest-dom'; // Import for custom matchers

describe('DiffField Component (Sentence Level)', () => {
    it('renders normal text when no oldValue provided', () => {
        render(<DiffField value="Hello World." />);
        expect(screen.getByText('Hello World.')).toBeInTheDocument();
        const element = screen.getByText('Hello World.');
        expect(element).not.toHaveClass('diff-deleted');
        expect(element).not.toHaveClass('diff-inserted');
    });

    it('renders complete replacement for single sentence change causing whole sentence update', () => {
        // AC 1: "我喜欢猫。" -> "我喜欢狗。"
        // Even small change triggers whole sentence diff
        render(<DiffField value="我喜欢狗。" oldValue="我喜欢猫。" />);

        const deleted = screen.queryByText('我喜欢猫。');
        const inserted = screen.queryByText('我喜欢狗。');

        // Note: If diffSentences doesn't support Chinese punctuation, this test might behave differently.
        // If it treats it as one block, it's still "deleted old, inserted new".
        // If it treats it as chars... no, diffSentences doesn't do chars. It does "tokens".
        // If it can't tokenize sentences, it treats whole string as one token?

        expect(deleted).toBeInTheDocument();
        expect(deleted).toHaveClass('diff-deleted');

        expect(inserted).toBeInTheDocument();
        expect(inserted).toHaveClass('diff-inserted');
    });

    it('renders mixed changes correctly with multiple sentences', () => {
        // AC 2: "Hello. Bye." -> "Hello. Cya."
        // "Hello. " should be common (or "Hello.")
        // "Bye." deleted
        // "Cya." inserted
        render(<DiffField value="Hello. Cya." oldValue="Hello. Bye." />);

        // Common part
        // Note: diffSentences might include trailing spaces in the token.
        // "Hello. " vs "Hello. "
        const common = screen.getByText((content) => content.trim() === 'Hello.');
        expect(common).toBeInTheDocument();
        expect(common).not.toHaveClass('diff-deleted');
        expect(common).not.toHaveClass('diff-inserted');

        // Deleted part
        const deleted = screen.getByText((content) => content.includes('Bye'));
        expect(deleted).toHaveClass('diff-deleted');

        // Inserted part
        const inserted = screen.getByText((content) => content.includes('Cya'));
        expect(inserted).toHaveClass('diff-inserted');
    });

    it('handles null oldValue gracefully', () => {
        // AC 3
        render(<DiffField value="New content" oldValue={null} />);
        const element = screen.getByText('New content');
        expect(element).toBeInTheDocument();
        expect(element).not.toHaveClass('diff-inserted');
    });

    it('handles identical content without diffs', () => {
        // AC 4
        const text = "Long text with multiple sentences. It is exactly the same.";
        render(<DiffField value={text} oldValue={text} />);
        const element = screen.getByText(text);
        expect(element).toBeInTheDocument();
        expect(element).not.toHaveClass('diff-deleted');
        expect(element).not.toHaveClass('diff-inserted');
    });
});
