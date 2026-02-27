# New Agents Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a robust test suite for the `new-agents` frontend and backend, focusing on the core agent logic (LLM tag parsing, artifact formatting, stream handling, state management) without touching UI components.

**Architecture:** 
1. **Frontend (Vitest)**: Extract tightly-coupled parsing and Markdown preprocessing logic from `llm.ts` and `ArtifactPane.tsx` into pure functions in `utils/`. Add tests for these utilities and the Zustand store.
2. **Backend (pytest)**: Expand existing Flask backend tests to cover SSE streaming, API proxy errors, and configuration boundaries.

**Tech Stack:** Vitest, React, Zustand, Flask, pytest, unittest.mock

---

### Task 1: Setup Vitest in Frontend

**Files:**
- Modify: `tools/new-agents/package.json`
- Modify: `tools/new-agents/vite.config.ts`

**Step 1: Install Vitest**
(Skip actual install if simulating plan execution without npm, but update `package.json`).

Modify `tools/new-agents/package.json` to include `"vitest": "^3.0.0"` in `devDependencies` and add `"test": "vitest run"` in `scripts`.

**Step 2: Update vite.config.ts**
Modify `tools/new-agents/vite.config.ts` to add vitest types if needed.
```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vite';
// ... rest of the file
export default defineConfig(({ mode }) => {
  // ...
  return {
    // ...
    test: {
      environment: 'jsdom',
      globals: true,
    }
  };
});
```

**Step 3: Commit**

```bash
cd tools/new-agents
npm install -D vitest @vitest/ui jsdom
git add package.json package-lock.json vite.config.ts
git commit -m "test(frontend): Setup Vitest for new-agents"
```

---

### Task 2: Extract & Test Markdown Preprocessor

**Files:**
- Create: `tools/new-agents/src/utils/markdownUtils.ts`
- Create: `tools/new-agents/src/__tests__/markdownUtils.test.ts`
- Modify: `tools/new-agents/src/components/ArtifactPane.tsx`

**Step 1: Write the failing test**

Create `tools/new-agents/src/__tests__/markdownUtils.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { preprocessMarkdown } from '../utils/markdownUtils';

describe('preprocessMarkdown', () => {
  it('should format simple mark tags', () => {
    const input = "Here is <mark>new text</mark>.";
    expect(preprocessMarkdown(input)).toBe("Here is <mark>new text</mark>.");
  });

  it('should split multiple list items within a single mark tag', () => {
    const input = "<mark>* Item 1 * Item 2</mark>";
    const result = preprocessMarkdown(input);
    expect(result).toContain('<mark>Item 1</mark>');
    expect(result).toContain('\n* <mark>Item 2</mark>');
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
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

Create `tools/new-agents/src/utils/markdownUtils.ts` and move the `preprocessMarkdown` function from `ArtifactPane.tsx` into it. Then import `preprocessMarkdown` in `ArtifactPane.tsx`.

**Step 4: Run test to verify it passes**

Run: `cd tools/new-agents && npm run test src/__tests__/markdownUtils.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/new-agents/src/utils/markdownUtils.ts tools/new-agents/src/__tests__/markdownUtils.test.ts tools/new-agents/src/components/ArtifactPane.tsx
git commit -m "test(frontend): Extract and test preprocessMarkdown"
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
import { describe, it, expect } from 'vitest';
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

  it('should handle incomplete tags during streaming', () => {
    const text = "<CHAT>Processing...";
    const result = parseLlmStreamChunk(text, "old doc");
    expect(result.chatResponse).toBe('Processing...');
  });

  it('should fallback to raw text if no CHAT tag', () => {
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
    chatResponse = fullText.replace(/<CHAT>/i, '').trim();
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

Modify `tools/new-agents/src/llm.ts` to use `parseLlmStreamChunk` around line 177 instead of inline parsing.

**Step 4: Run test to verify it passes**

Run: `cd tools/new-agents && npm run test src/__tests__/llmParser.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/new-agents/src/utils/llmParser.ts tools/new-agents/src/__tests__/llmParser.test.ts tools/new-agents/src/llm.ts
git commit -m "test(frontend): Extract and test llm chunk parsing"
```

---

### Task 4: Store Logic Tests (Zustand)

**Files:**
- Create: `tools/new-agents/src/__tests__/store.test.ts`

**Step 1: Write the failing test**

Create `tools/new-agents/src/__tests__/store.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest';
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

  it('should correctly set artifacts', () => {
    useStore.getState().setArtifactContent('New Content');
    const state = useStore.getState();
    
    expect(state.artifactContent).toBe('New Content');
    expect(state.stageArtifacts[0]).toBe('New Content');
  });
});
```

**Step 2: Run test to verify it works**

Run: `cd tools/new-agents && npm run test src/__tests__/store.test.ts`
Expected: PASS (if Zustand store behavior is as implemented. If not, fix store).

**Step 3: Commit**

```bash
git add tools/new-agents/src/__tests__/store.test.ts
git commit -m "test(frontend): Add Zustand store state logic tests"
```

---

### Task 5: Backend SSE Proxy Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_api.py`

**Step 1: Write the failing tests**

Append to `tools/new-agents/backend/tests/test_api.py`:
```python
from unittest.mock import patch, MagicMock
from app import app
import json

def test_chat_stream_missing_config(client):
    """Test streaming when no default configuration exists."""
    response = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 503
    assert "系统未配置默认 LLM" in response.json["error"]

@patch('app.OpenAI')
def test_chat_stream_success(mock_openai, client):
    """Test successful SSE stream."""
    from app import get_session
    from models import LlmConfig
    
    with app.app_context():
        session = get_session()
        config = LlmConfig(config_key='default', api_key='sk-123', base_url='http://t', model='gpt-4')
        session.add(config)
        session.commit()

    # Mock the return values for stream
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    class MockDelta:
        def __init__(self, content):
            self.content = content
    class MockChoice:
        def __init__(self, delta):
            self.delta = delta
    class MockChunk:
        def __init__(self, content):
            self.choices = [MockChoice(MockDelta(content))] if content else []
    
    mock_client.chat.completions.create.return_value = [
        MockChunk("Hello"),
        MockChunk(" World")
    ]

    response = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'
    
    # Process the stream generator
    data = response.get_data(as_text=True)
    assert 'data: {"content": "Hello"}' in data
    assert 'data: {"content": " World"}' in data
    assert 'data: [DONE]' in data

@patch('app.OpenAI')
def test_chat_stream_openai_error(mock_openai, client):
    """Test handling of OpenAI exception during stream creation."""
    from app import get_session
    from models import LlmConfig
    
    # Using existing default config from previous tests can be flaky, 
    # but we're creating new app states if fixture handles it right.
    with app.app_context():
        session = get_session()
        # insert if not exists to avoid uniqueness errs in tests using same DB
        if not session.query(LlmConfig).filter_by(config_key='default').first():
            session.add(LlmConfig(config_key='default', api_key='sk', base_url='x', model='y'))
            session.commit()

    mock_openai.side_effect = Exception("OpenAI API unreachable")
    
    response = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200 # It returns 200 and streams the error
    
    data = response.get_data(as_text=True)
    assert 'data: {"error": "OpenAI API unreachable"}' in data
```

**Step 2: Run test to verify it behaves correctly**

Run: `cd tools/new-agents/backend && pytest tests/test_api.py -c pytest.ini`
Expected: PASS (These tests mock behavior correctly matching `app.py`). Note: if tests fail due to DB cleanup issues in fixture, verify that `conftest.py` tears down DB per test or adapt session handling.

**Step 3: Commit**

```bash
git add tools/new-agents/backend/tests/test_api.py
git commit -m "test(backend): Add SSE streaming tests for LLM proxy"
```

---
