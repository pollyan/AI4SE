# New Agents Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Provide comprehensive unit testing for the `new-agents` frontend logic (Vitest) and backend streaming API (pytest), decoupling core business logic from UI components via TDD.

**Architecture:** 
1. **Frontend**: Install Vitest. Extract markdown preprocessing and LLM tag stream parsing (`<CHAT>`, `<ARTIFACT>`, `<ACTION>`) into pure functions. Write tests for these utils and the Zustand store.
2. **Backend**: Extend the Flask `test_api.py` to cover the `/api/chat/stream` SSE proxy endpoint by mocking the OpenAI client, covering both success streams and error states.

**Tech Stack:** Vitest, React, Zustand, Flask, pytest, unittest.mock

---

### Task 1: Setup Vitest for Frontend

**Files:**
- Modify: `tools/new-agents/package.json`
- Modify: `tools/new-agents/vite.config.ts`

**Step 1: Write the failing test**

We don't have a test yet, we need to install dependencies.

**Step 2: Run test to verify it fails**

Run: `cd tools/new-agents && npm run test`
Expected: FAIL containing "missing script: test"

**Step 3: Write minimal implementation**

Modify `tools/new-agents/vite.config.ts` by adding vitest reference and config inside `defineConfig`:
```typescript
/// <reference types="vitest" />
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    base: '/new-agents/',
    plugins: [react(), tailwindcss()],
    define: {
      'process.env.LLM_API_KEY': JSON.stringify(env.LLM_API_KEY),
      'process.env.LLM_BASE_URL': JSON.stringify(env.LLM_BASE_URL),
      'process.env.LLM_MODEL': JSON.stringify(env.LLM_MODEL),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
    },
    test: {
      environment: 'jsdom',
      globals: true,
    },
  };
});
```

Run command: 
```bash
cd tools/new-agents
npm install -D vitest @vitest/ui jsdom
npm pkg set scripts.test="vitest run"
```

**Step 4: Run test to verify it passes**

Run: `cd tools/new-agents && npm run test`
Expected: PASS (It will report "No test files found", which is a successful run for Vitest with no tests).

**Step 5: Commit**

```bash
cd tools/new-agents
git add package.json package-lock.json vite.config.ts
git commit -m "test(frontend): Setup Vitest for new-agents"
```

---

### Task 2: Extract & Test Markdown Preprocessor

**Files:**
- Create: `tools/new-agents/src/utils/markdownUtils.ts`
- Create: `tools/new-agents/src/__tests__/markdownUtils.test.ts`
- Modify: `tools/new-agents/src/components/ArtifactPane.tsx:43-55`

**Step 1: Write the failing test**

Create `tools/new-agents/src/__tests__/markdownUtils.test.ts`:
```typescript
import { preprocessMarkdown } from '../utils/markdownUtils';

describe('preprocessMarkdown', () => {
  it('should format simple mark tags', () => {
    const input = "Here is <mark>new text</mark>.";
    expect(preprocessMarkdown(input)).toBe("Here is <mark>new text</mark>.");
  });

  it('should split multiple list items within a single mark tag', () => {
    const input = "<mark>* Item 1\n* Item 2</mark>";
    const result = preprocessMarkdown(input);
    expect(result).toBe("* <mark>Item 1</mark>\n* <mark>Item 2</mark>");
  });

  it('should fix block prefixes wrapped in mark tags', () => {
    const input = "<mark>### Header</mark>\n<mark>1. List item</mark>";
    const result = preprocessMarkdown(input);
    expect(result).toBe("### <mark>Header</mark>\n1. <mark>List item</mark>");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd tools/new-agents && npm run test src/__tests__/markdownUtils.test.ts`
Expected: FAIL with "Cannot find module" or function not defined.

**Step 3: Write minimal implementation**

Create `tools/new-agents/src/utils/markdownUtils.ts`:
```typescript
export const preprocessMarkdown = (content: string) => {
  if (!content) return '';
  return content
    .replace(/<mark>([\s\S]*?)<\/mark>/g, (match, p1) => {
      if (p1.includes('\n* ') || p1.includes('\n- ')) {
        return p1.split('\n').map((line: string) => {
          if (line.trim() && (line.startsWith('* ') || line.startsWith('- '))) {
            return `${line.substring(0, 2)}<mark>${line.substring(2)}</mark>`;
          }
          return line ? `<mark>${line}</mark>` : line;
        }).join('\n');
      }
      const headerMatch = p1.match(/^(#+\s)(.*)$/);
      if (headerMatch) {
        return `${headerMatch[1]}<mark>${headerMatch[2]}</mark>`;
      }
      const listMatch = p1.match(/^(\d+\.\s)(.*)$/);
      if (listMatch) {
         return `${listMatch[1]}<mark>${listMatch[2]}</mark>`;
      }
      return match;
    });
};
```

Modify `tools/new-agents/src/components/ArtifactPane.tsx` to remove its internal `preprocessMarkdown` and import the new one:
```typescript
import { preprocessMarkdown } from '../utils/markdownUtils';
```

**Step 4: Run test to verify it passes**

Run: `cd tools/new-agents && npm run test src/__tests__/markdownUtils.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/new-agents/src/utils/markdownUtils.ts tools/new-agents/src/__tests__/markdownUtils.test.ts tools/new-agents/src/components/ArtifactPane.tsx
git commit -m "test(frontend): Extract and test preprocessMarkdown logic"
```

---

### Task 3: Extract & Test LLM Tag Parser

**Files:**
- Create: `tools/new-agents/src/utils/llmParser.ts`
- Create: `tools/new-agents/src/__tests__/llmParser.test.ts`
- Modify: `tools/new-agents/src/llm.ts`

**Step 1: Write the failing test**

Create `tools/new-agents/src/__tests__/llmParser.test.ts`:
```typescript
import { parseLlmStreamChunk } from '../utils/llmParser';

describe('parseLlmStreamChunk', () => {
  it('should parse CHAT, ARTIFACT and ACTION tags', () => {
    const text = "<CHAT>Hello</CHAT><ACTION>NEXT_STAGE</ACTION><ARTIFACT># Doc</ARTIFACT>";
    const result = parseLlmStreamChunk(text, "old doc");
    
    expect(result.chatResponse).toBe('Hello');
    expect(result.action).toBe('NEXT_STAGE');
    expect(result.newArtifact).toBe('# Doc');
    expect(result.hasArtifactUpdate).toBe(true);
  });

  it('should handle NO_UPDATE artifact', () => {
    const text = "<CHAT>OK</CHAT><ARTIFACT>NO_UPDATE</ARTIFACT>";
    const result = parseLlmStreamChunk(text, "old doc");
    
    expect(result.newArtifact).toBe('old doc');
    expect(result.hasArtifactUpdate).toBe(false);
  });

  it('should fallback to raw text if no tags exist', () => {
    const text = "Just raw text";
    const result = parseLlmStreamChunk(text, "old doc");
    expect(result.chatResponse).toBe('Just raw text');
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd tools/new-agents && npm run test src/__tests__/llmParser.test.ts`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `tools/new-agents/src/utils/llmParser.ts`:
```typescript
export function parseLlmStreamChunk(fullText: string, currentArtifact: string) {
  let chatResponse = '';
  let newArtifact = currentArtifact;
  let action = '';
  let hasArtifactUpdate = false;

  const chatMatch = fullText.match(/<CHAT>([\s\S]*?)(?:<\/CHAT>|$)/i);
  if (chatMatch) {
    chatResponse = chatMatch[1].trim();
  } else {
    chatResponse = fullText.replace(/<\/?(?:CHAT|ARTIFACT|ACTION)>/gi, '').trim();
    if (!chatResponse) chatResponse = fullText.trim();
  }

  const artifactMatch = fullText.match(/<ARTIFACT>([\s\S]*?)(?:<\/ARTIFACT>|$)/i);
  if (artifactMatch) {
    const extractedArtifact = artifactMatch[1].trim();
    if (extractedArtifact && !extractedArtifact.includes('NO_UPDATE')) {
      newArtifact = extractedArtifact;
      hasArtifactUpdate = true;
    }
  }

  const actionMatch = fullText.match(/<ACTION>([\s\S]*?)(?:<\/ACTION>|$)/i);
  if (actionMatch) {
    action = actionMatch[1].trim();
  }

  return { chatResponse, newArtifact, action, hasArtifactUpdate };
}
```

Modify `tools/new-agents/src/llm.ts` inside `callLlmStream` (around line 183):
Import: `import { parseLlmStreamChunk } from './utils/llmParser';`
Replace the manual parsing logic with:
```typescript
const { chatResponse, newArtifact, action, hasArtifactUpdate } = parseLlmStreamChunk(fullText, currentArtifactContent);
```
Make sure `currentArtifactContent` tracks the current known value properly if needed, but adapt `llm.ts` to cleanly use this new extraction.

**Step 4: Run test to verify it passes**

Run: `cd tools/new-agents && npm run test src/__tests__/llmParser.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/new-agents/src/utils/llmParser.ts tools/new-agents/src/__tests__/llmParser.test.ts tools/new-agents/src/llm.ts
git commit -m "test(frontend): Extract and test llm chunk parsing"
```

---

### Task 4: Zustand Store State Tests

**Files:**
- Create: `tools/new-agents/src/__tests__/store.test.ts`

**Step 1: Write the failing test**

Create `tools/new-agents/src/__tests__/store.test.ts`:
```typescript
import { useStore } from '../store';

describe('Zustand Store', () => {
  beforeEach(() => {
    useStore.getState().clearHistory();
  });

  it('should clear history to defaults', () => {
    const state = useStore.getState();
    state.addMessage({ id: '1', role: 'user', content: 'hello', timestamp: 123 });
    state.setStageIndex(2);
    
    useStore.getState().clearHistory();
    const newState = useStore.getState();
    
    expect(newState.chatHistory).toHaveLength(0);
    expect(newState.stageIndex).toBe(0);
  });

  it('should transition to next stage and preserve artifacts', () => {
    useStore.getState().transitionToNextStage(0, 'Stage 0 Data');
    const state = useStore.getState();
    
    expect(state.stageIndex).toBe(1);
    expect(state.stageArtifacts[0]).toBe('Stage 0 Data');
  });

  it('should switch workflows and clear state', () => {
    useStore.getState().setStageIndex(2);
    useStore.getState().setWorkflow('REQ_REVIEW');
    const state = useStore.getState();
    
    expect(state.workflow).toBe('REQ_REVIEW');
    expect(state.stageIndex).toBe(0);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd tools/new-agents && npm run test src/__tests__/store.test.ts`
Expected: Likely PASS correctly without changes, as logic is already implemented. If it fails due to missing environment issues, fix imports.

**Step 3: Write minimal implementation**

No implementation file changes needed if the test passes.

**Step 4: Run test to verify it passes**

Run: `cd tools/new-agents && npm run test src/__tests__/store.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/new-agents/src/__tests__/store.test.ts
git commit -m "test(frontend): Add Zustand store unit tests"
```

---

### Task 5: Backend SSE Streaming Tests 

**Files:**
- Modify: `tools/new-agents/backend/tests/test_api.py`

**Step 1: Write the failing test**

Append to `tools/new-agents/backend/tests/test_api.py`:
```python
from unittest.mock import patch, MagicMock

def test_chat_stream_missing_config(client):
    response = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 503
    assert "系统未配置" in response.json["error"]

@patch('app.OpenAI')
def test_chat_stream_success(mock_openai, client):
    from app import get_session
    from models import LlmConfig
    
    with app.app_context():
        session = get_session()
        config = session.query(LlmConfig).filter_by(config_key='default').first()
        if not config:
            config = LlmConfig(config_key='default', api_key='sk-123', base_url='http://t', model='gpt-4')
            session.add(config)
            session.commit()

    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    class MockDelta:
        def __init__(self, content): self.content = content
    class MockChoice:
        def __init__(self, delta): self.delta = delta
    class MockChunk:
        def __init__(self, content): self.choices = [MockChoice(MockDelta(content))]

    mock_client.chat.completions.create.return_value = [MockChunk("Hello"), MockChunk(" World")]

    response = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'
    
    data = response.get_data(as_text=True)
    assert 'data: {"content": "Hello"}' in data
    assert 'data: {"content": " World"}' in data
    assert 'data: [DONE]' in data

@patch('app.OpenAI')
def test_chat_stream_openai_error(mock_openai, client):
    from app import get_session
    from models import LlmConfig
    
    with app.app_context():
        session = get_session()
        if not session.query(LlmConfig).filter_by(config_key='default').first():
            session.add(LlmConfig(config_key='default', api_key='sk', base_url='x', model='y'))
            session.commit()

    mock_openai.side_effect = Exception("OpenAI API unreachable")
    
    response = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200
    data = response.get_data(as_text=True)
    assert 'data: {"error": "OpenAI API unreachable"}' in data
```

**Step 2: Run test to verify it fails**

Run: `cd tools/new-agents/backend && pytest tests/test_api.py -v`
Expected: If `app.py` doesn't exist to these specs it fails; but since it does exist, we expect it to PASS. Some logic handling exceptions may need to catch it differently. If it passes outright, we have protected against regressions.

**Step 3: Write minimal implementation**

Not required, but fix `app.py` if the error strings don't align with assertions.

**Step 4: Run test to verify it passes**

Run: `cd tools/new-agents/backend && pytest tests/test_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/new-agents/backend/tests/test_api.py
git commit -m "test(backend): Add SSE chat stream tests"
```
