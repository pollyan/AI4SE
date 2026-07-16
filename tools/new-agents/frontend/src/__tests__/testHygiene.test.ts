import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { basename, join, relative } from 'node:path';

const sourceRoot = join(process.cwd(), 'src');
const testFilePattern = /\.test\.(ts|tsx)$/;
const typeSafetyFiles = [
    join(sourceRoot, 'components', 'ArtifactPane.tsx'),
    join(sourceRoot, 'components', 'ChatPane.tsx'),
    join(sourceRoot, 'components', 'Mermaid.tsx'),
    join(sourceRoot, 'components', 'markdownCodeRenderer.tsx'),
    join(sourceRoot, 'components', '__tests__', 'Mermaid.test.tsx'),
    join(sourceRoot, 'components', '__tests__', 'markdownCodeRenderer.test.tsx'),
    join(sourceRoot, 'core', '__tests__', 'llm.test.ts'),
    join(sourceRoot, 'services', 'chatService.ts'),
];

function collectTestFiles(dir: string): string[] {
    return readdirSync(dir).flatMap((entry) => {
        const fullPath = join(dir, entry);
        if (fullPath.includes(`${join('src', 'core', '__tests__', 'smoke')}`)) {
            return [];
        }
        if (statSync(fullPath).isDirectory()) {
            return collectTestFiles(fullPath);
        }
        return testFilePattern.test(fullPath) ? [fullPath] : [];
    });
}

function collectSourceFiles(dir: string): string[] {
    return readdirSync(dir).flatMap((entry) => {
        const fullPath = join(dir, entry);
        if (statSync(fullPath).isDirectory()) {
            return collectSourceFiles(fullPath);
        }
        return /\.(ts|tsx)$/.test(fullPath) ? [fullPath] : [];
    });
}

function isTestSourceFile(file: string): boolean {
    return testFilePattern.test(file) || file.split(/[\\/]/).includes('__tests__');
}

describe('test hygiene', () => {
    it('does not leave console diagnostics in non-smoke tests', () => {
        const offenders = collectTestFiles(sourceRoot)
            .filter((file) => !file.endsWith('testHygiene.test.ts'))
            .flatMap((file) => {
                const lines = readFileSync(file, 'utf8').split('\n');
                return lines
                    .map((line, index) => ({ line, lineNumber: index + 1 }))
                    .filter(
                        ({ line }) => line.includes('console.log')
                            || line.includes('console.error')
                    )
                    .map(({ lineNumber }) => `${relative(process.cwd(), file)}:${lineNumber}`);
            });

        expect(offenders).toEqual([]);
    });

    it('does not leave console diagnostics in production frontend source', () => {
        const offenders = collectSourceFiles(sourceRoot)
            .filter((file) => !isTestSourceFile(file))
            .flatMap((file) => {
                const lines = readFileSync(file, 'utf8').split('\n');
                return lines
                    .map((line, index) => ({ line, lineNumber: index + 1 }))
                    .filter(
                        ({ line }) => line.includes('console.log')
                            || line.includes('console.error')
                            || line.includes('console.warn')
                    )
                    .map(({ lineNumber }) => `${relative(process.cwd(), file)}:${lineNumber}`);
            });

        expect(offenders).toEqual([]);
    });

    it('does not keep diagnostic test files in the non-smoke suite', () => {
        const offenders = collectTestFiles(sourceRoot)
            .filter((file) => !file.endsWith('testHygiene.test.ts'))
            .filter((file) => /(?:^|[-_.])diag(?:[-_.]|$)|diagnostic/i.test(basename(file)))
            .map((file) => relative(process.cwd(), file));

        expect(offenders).toEqual([]);
    });

    it('does not use TypeScript escape hatches in checked agent frontend code', () => {
        const forbiddenPatterns: RegExp[] = [
            /as any/,
            /@ts-ignore/,
            /@ts-expect-error/,
            /:\s*any\b/,
            /catch \([^)]*: any\)/,
            /\}: any\)/,
        ];
        const offenders = typeSafetyFiles.flatMap((file) => {
            const lines = readFileSync(file, 'utf8').split('\n');
            return lines
                .map((line, index) => ({ line, lineNumber: index + 1 }))
                .filter(({ line }) => forbiddenPatterns.some((pattern) => pattern.test(line)))
                .map(({ lineNumber }) => `${relative(process.cwd(), file)}:${lineNumber}`);
        });

        expect(offenders).toEqual([]);
    });

    it('does not call the legacy chat stream endpoint from frontend source', () => {
        const offenders = readdirSync(sourceRoot, { recursive: true, withFileTypes: true })
            .filter((entry) => entry.isFile())
            .map((entry) => join(entry.parentPath, entry.name))
            .filter((file) => /\.(ts|tsx)$/.test(file))
            .filter((file) => !file.endsWith('testHygiene.test.ts'))
            .flatMap((file) => {
                const lines = readFileSync(file, 'utf8').split('\n');
                return lines
                    .map((line, index) => ({ line, lineNumber: index + 1 }))
                    .filter(({ line }) => line.includes('/new-agents/api/chat/stream'))
                    .map(({ lineNumber }) => `${relative(process.cwd(), file)}:${lineNumber}`);
            });

        expect(offenders).toEqual([]);
    });

    it('does not keep legacy direct LLM protocol in the main agent path', () => {
        const checkedFiles = [
            join(sourceRoot, 'core', 'llm.ts'),
            join(sourceRoot, 'services', 'chatService.ts'),
        ];
        const forbiddenPatterns: RegExp[] = [
            /from ['"]openai['"]/,
            /new OpenAI\(/,
            /parseLlmStreamChunk/,
            /detectArtifactTruncation/,
            /llmParser/,
            /<CHAT>|<ARTIFACT>|<ACTION>|NO_UPDATE/,
        ];
        const offenders = checkedFiles.flatMap((file) => {
            const lines = readFileSync(file, 'utf8').split('\n');
            return lines
                .map((line, index) => ({ line, lineNumber: index + 1 }))
                .filter(({ line }) => forbiddenPatterns.some((pattern) => pattern.test(line)))
                .map(({ lineNumber }) => `${relative(process.cwd(), file)}:${lineNumber}`);
        });

        expect(offenders).toEqual([]);
    });

    it('does not statically import Mermaid in the main agent request path', () => {
        const checkedFiles = [
            join(sourceRoot, 'core', 'llm.ts'),
            join(sourceRoot, 'components', 'Mermaid.tsx'),
        ];
        const offenders = checkedFiles.flatMap((file) => {
            return readFileSync(file, 'utf8')
                .split('\n')
                .map((line, index) => ({ line, lineNumber: index + 1 }))
                .filter(({ line }) =>
                    /import\s+mermaid\s+from\s+['"]mermaid['"]/.test(line)
                )
                .map(({ lineNumber }) => `${relative(process.cwd(), file)}:${lineNumber}`);
        });

        expect(offenders).toEqual([]);
    });

    it('does not statically import heavy workspace panels into the route shell', () => {
        const file = join(sourceRoot, 'pages', 'Workspace.tsx');
        const forbiddenPatterns: RegExp[] = [
            /import\s+\{\s*ChatPane\s*\}\s+from\s+['"]\.\.\/components\/ChatPane['"]/,
            /import\s+\{\s*ArtifactPane\s*\}\s+from\s+['"]\.\.\/components\/ArtifactPane['"]/,
        ];
        const offenders = readFileSync(file, 'utf8')
            .split('\n')
            .map((line, index) => ({ line, lineNumber: index + 1 }))
            .filter(({ line }) => forbiddenPatterns.some((pattern) => pattern.test(line)))
            .map(({ lineNumber }) => `${relative(process.cwd(), file)}:${lineNumber}`);

        expect(offenders).toEqual([]);
    });

    it('keeps the workspace shell dark and height-constrained during streaming visual renders', () => {
        const indexCss = readFileSync(join(sourceRoot, 'index.css'), 'utf8');
        const workspace = readFileSync(join(sourceRoot, 'pages', 'Workspace.tsx'), 'utf8');
        const artifactPane = readFileSync(join(sourceRoot, 'components', 'ArtifactPane.tsx'), 'utf8');
        const expectClassTokens = (source: string, selectorPattern: RegExp, tokens: string[]) => {
            const className = source.match(selectorPattern)?.[1] ?? '';
            expect(tokens.filter((token) => !className.split(/\s+/).includes(token))).toEqual([]);
        };

        expect(indexCss).toMatch(/html,\s*body,\s*#root\s*\{[^}]*background:\s*#0B1120;/s);
        expectClassTokens(workspace, /<div className="([^"]*)">/, ['h-[100dvh]', 'min-h-0', 'overflow-hidden']);
        expectClassTokens(workspace, /<main className="([^"]*)">/, ['flex-1', 'min-h-0', 'overflow-hidden']);
        expectClassTokens(
            artifactPane,
            /<section[^>]*data-testid="artifact-pane"[^>]*className="([^"]*)"[^>]*>/,
            ['min-h-0', 'overflow-hidden', 'bg-grid-pattern']
        );
        expectClassTokens(artifactPane, /<div className="([^"]*overflow-y-auto[^"]*)">/, ['flex-1', 'min-h-0', 'overflow-y-auto']);
    });
});
