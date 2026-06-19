export type LineDiffEntry = {
    type: 'added' | 'removed' | 'unchanged';
    content: string;
};

const splitLines = (content: string): string[] => (
    content.replace(/\r\n/g, '\n').split('\n')
);

export const buildLineDiff = (
    previousContent: string,
    currentContent: string,
): LineDiffEntry[] => {
    const previousLines = splitLines(previousContent);
    const currentLines = splitLines(currentContent);
    const table = Array.from(
        { length: previousLines.length + 1 },
        () => Array(currentLines.length + 1).fill(0) as number[],
    );

    for (let leftIndex = previousLines.length - 1; leftIndex >= 0; leftIndex -= 1) {
        for (let rightIndex = currentLines.length - 1; rightIndex >= 0; rightIndex -= 1) {
            if (previousLines[leftIndex] === currentLines[rightIndex]) {
                table[leftIndex][rightIndex] = table[leftIndex + 1][rightIndex + 1] + 1;
            } else {
                table[leftIndex][rightIndex] = Math.max(
                    table[leftIndex + 1][rightIndex],
                    table[leftIndex][rightIndex + 1],
                );
            }
        }
    }

    const diff: LineDiffEntry[] = [];
    let leftIndex = 0;
    let rightIndex = 0;
    while (leftIndex < previousLines.length && rightIndex < currentLines.length) {
        if (previousLines[leftIndex] === currentLines[rightIndex]) {
            diff.push({ type: 'unchanged', content: previousLines[leftIndex] });
            leftIndex += 1;
            rightIndex += 1;
        } else if (table[leftIndex + 1][rightIndex] >= table[leftIndex][rightIndex + 1]) {
            diff.push({ type: 'removed', content: previousLines[leftIndex] });
            leftIndex += 1;
        } else {
            diff.push({ type: 'added', content: currentLines[rightIndex] });
            rightIndex += 1;
        }
    }

    while (leftIndex < previousLines.length) {
        diff.push({ type: 'removed', content: previousLines[leftIndex] });
        leftIndex += 1;
    }
    while (rightIndex < currentLines.length) {
        diff.push({ type: 'added', content: currentLines[rightIndex] });
        rightIndex += 1;
    }

    return diff;
};
