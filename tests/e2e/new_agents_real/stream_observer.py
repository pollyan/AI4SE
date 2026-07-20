from __future__ import annotations

from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

HASH_TEXT_INSTALL_SCRIPT = r"""
(() => {
  const initialState = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ];
  const roundConstants = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ];
  const rotateRight = (value, count) => (
    (value >>> count) | (value << (32 - count))
  ) >>> 0;
  window.__ai4seHashText = (value) => {
    const bytes = new TextEncoder().encode(value);
    const paddedLength = Math.ceil((bytes.length + 9) / 64) * 64;
    const padded = new Uint8Array(paddedLength);
    padded.set(bytes);
    padded[bytes.length] = 0x80;
    const bitLength = bytes.length * 8;
    const view = new DataView(padded.buffer);
    view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000));
    view.setUint32(paddedLength - 4, bitLength >>> 0);
    const state = [...initialState];
    const words = new Uint32Array(64);
    for (let offset = 0; offset < paddedLength; offset += 64) {
      for (let index = 0; index < 16; index += 1) {
        words[index] = view.getUint32(offset + index * 4);
      }
      for (let index = 16; index < 64; index += 1) {
        const before15 = words[index - 15];
        const before2 = words[index - 2];
        const sigma0 = (
          rotateRight(before15, 7)
          ^ rotateRight(before15, 18)
          ^ (before15 >>> 3)
        ) >>> 0;
        const sigma1 = (
          rotateRight(before2, 17)
          ^ rotateRight(before2, 19)
          ^ (before2 >>> 10)
        ) >>> 0;
        words[index] = (
          words[index - 16] + sigma0 + words[index - 7] + sigma1
        ) >>> 0;
      }
      let [a, b, c, d, e, f, g, h] = state;
      for (let index = 0; index < 64; index += 1) {
        const upperSigma1 = (
          rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25)
        ) >>> 0;
        const choice = ((e & f) ^ (~e & g)) >>> 0;
        const temp1 = (
          h + upperSigma1 + choice + roundConstants[index] + words[index]
        ) >>> 0;
        const upperSigma0 = (
          rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22)
        ) >>> 0;
        const majority = ((a & b) ^ (a & c) ^ (b & c)) >>> 0;
        const temp2 = (upperSigma0 + majority) >>> 0;
        h = g;
        g = f;
        f = e;
        e = (d + temp1) >>> 0;
        d = c;
        c = b;
        b = a;
        a = (temp1 + temp2) >>> 0;
      }
      state[0] = (state[0] + a) >>> 0;
      state[1] = (state[1] + b) >>> 0;
      state[2] = (state[2] + c) >>> 0;
      state[3] = (state[3] + d) >>> 0;
      state[4] = (state[4] + e) >>> 0;
      state[5] = (state[5] + f) >>> 0;
      state[6] = (state[6] + g) >>> 0;
      state[7] = (state[7] + h) >>> 0;
    }
    return `sha256-${state
      .map((word) => word.toString(16).padStart(8, '0'))
      .join('')}`;
  };
})();
"""

STREAM_OBSERVER_SCRIPT = HASH_TEXT_INSTALL_SCRIPT + r"""
(() => {
  const originalFetch = window.fetch.bind(window);
  const hashText = window.__ai4seHashText;
  const headingsOf = (value) => (
    value.match(/^#{1,6}\s+.+$/gm) || []
  ).map((heading) => heading.trim());
  const metadataHeadingPattern = /^#{1,3}\s+(?:\d+\.\s+)?(?:文档|评审|报告)信息$/;
  const headingSummary = (heading, identity = heading) => ({
    hash: hashText(identity),
    level: heading.match(/^#+/)?.[0].length || 0,
    metadata: metadataHeadingPattern.test(heading),
  });
  const headingSummariesOf = (headings) => {
    const path = [];
    return headings.map((heading) => {
      const level = heading.match(/^#+/)?.[0].length || 0;
      path.length = Math.max(0, level - 1);
      path[level - 1] = heading;
      return headingSummary(heading, path.filter(Boolean).join('\n'));
    });
  };
  const sectionsOf = (value, previousSections = []) => {
    const matches = [...value.matchAll(/^#{1,6}\s+.+$/gm)];
    const summaries = headingSummariesOf(
      matches.map((match) => match[0].trim())
    );
    return matches.map((match, index) => {
      const end = matches[index + 1]?.index ?? value.length;
      const text = value.slice(match.index, end).trim();
      const heading = match[0].trim();
      const summary = summaries[index];
      const previousSection = previousSections.find(
        (section) => section.headingHash === summary.hash
      );
      return {
        headingHash: summary.hash,
        headingLevel: summary.level,
        metadata: summary.metadata,
        hash: hashText(text),
        length: text.length,
        previousPrefixHash: previousSection
          ? hashText(text.slice(0, previousSection.length))
          : null,
      };
    });
  };
  const sectionMonotonicReason = (value, previous) => {
    if (!previous) return 'ok';
    const beforeSections = sectionsOf(previous);
    const before = beforeSections.filter((section) => !section.metadata);
    const current = sectionsOf(value, beforeSections).filter(
      (section) => !section.metadata
    );
    const hasDuplicateHeadings = (sections) => (
      new Set(sections.map((section) => section.headingHash)).size !== sections.length
    );
    if (hasDuplicateHeadings(before) || hasDuplicateHeadings(current)) {
      return 'duplicate_heading';
    }
    const isOrderedSubsequence = (expected, actual, matches) => {
      let actualIndex = 0;
      return expected.every((item) => {
        while (actualIndex < actual.length && !matches(item, actual[actualIndex])) {
          actualIndex += 1;
        }
        if (actualIndex >= actual.length) return false;
        actualIndex += 1;
        return true;
      });
    };
    const headingsRemainOrdered = isOrderedSubsequence(
      before,
      current,
      (previousSection, currentSection) => (
        previousSection.headingHash === currentSection.headingHash
      ),
    );
    const stableSectionsRemainExact = isOrderedSubsequence(
      before.slice(0, -1),
      current,
      (previousSection, currentSection) => (
        previousSection.headingHash === currentSection.headingHash
        && previousSection.hash === currentSection.hash
      ),
    );
    const previousTail = before.at(-1);
    const currentTail = current.find(
      (section) => section.headingHash === previousTail?.headingHash
    );
    const activeTailKeepsPrefix = !previousTail || (
      currentTail?.previousPrefixHash === previousTail.hash
    );
    if (!headingsRemainOrdered) return 'heading_order';
    if (!stableSectionsRemainExact) return 'stable_section_rewrite';
    if (!activeTailKeepsPrefix) return 'active_tail_rewrite';
    return 'ok';
  };
  const metadataOf = (value, headings) => {
    const index = headings.findIndex((heading) => metadataHeadingPattern.test(heading));
    if (index < 0) return null;
    const heading = headings[index];
    const summary = headingSummariesOf(headings)[index];
    const start = value.indexOf(heading);
    const remainder = value.slice(start + heading.length);
    const nextHeading = remainder.search(/^#{1,6}\s+.+$/m);
    const section = nextHeading >= 0 ? remainder.slice(0, nextHeading) : remainder;
    return {
      headingHash: summary.hash,
      headingLevel: summary.level,
      index,
      isFinal: index === headings.length - 1,
      compact: section.includes('文档元信息：'),
      hasTable: /^\s*\|.*\|\s*$/m.test(section),
    };
  };
  const summarizeText = (value, previous, kind) => {
    const rawHeadings = headingsOf(value);
    const monotonicReason = kind === 'artifact'
      ? sectionMonotonicReason(value, previous)
      : (!previous || value.startsWith(previous) ? 'ok' : 'source_prefix_rewrite');
    return {
      length: value.length,
      hash: hashText(value),
      previousLength: previous?.length || 0,
      previousHash: previous ? hashText(previous) : null,
      currentPrefixHash: previous
        ? hashText(value.slice(0, previous.length))
        : null,
      headings: headingSummariesOf(rawHeadings),
      sections: kind === 'artifact'
        ? sectionsOf(value, previous ? sectionsOf(previous) : [])
        : [],
      monotonic: monotonicReason === 'ok',
      monotonicReason,
      metadata: metadataOf(value, rawHeadings),
    };
  };
  const safeDiagnosticToken = (value, maxLength) => {
    if (typeof value !== 'string' || value.length < 1 || value.length > maxLength) {
      return null;
    }
    if (!/^[A-Za-z0-9_.-]+$/.test(value)) return null;
    if (/(?:api.?key|authorization|bearer|password|secret|token|sk-)/i.test(value)) {
      return null;
    }
    return value;
  };
  const projectDiagnostic = (value) => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    const diagnostic = {};
    const phase = safeDiagnosticToken(value.phase, 64);
    const fieldPath = safeDiagnosticToken(value.fieldPath, 256);
    const validator = safeDiagnosticToken(value.validator, 128);
    if (phase) diagnostic.phase = phase;
    if (fieldPath) diagnostic.fieldPath = fieldPath;
    if (validator) diagnostic.validator = validator;
    if (typeof value.retryable === 'boolean') diagnostic.retryable = value.retryable;
    return Object.keys(diagnostic).length ? diagnostic : null;
  };
  const allowedErrorCodes = new Set([
    'LLM_ERROR',
    'DEFAULT_LLM_CONFIG_MISSING',
    'SCHEMA_VALIDATION_FAILED',
    'CONTRACT_VALIDATION_FAILED',
    'VISUAL_VALIDATION_FAILED',
    'REQUEST_VALIDATION_FAILED',
    'AGENT_RUNTIME_UNAVAILABLE',
    'PERSISTENCE_FAILED',
    'REQUEST_IN_PROGRESS',
    'PERSISTENCE_CONFLICT',
    'REQUEST_IDENTITY_CONFLICT',
  ]);
  const projectEvent = (parsed, trace) => {
    if (parsed.type === 'agent_retry') {
      trace.attempt += 1;
      trace.transient.lastChat = '';
      trace.transient.lastArtifact = '';
      return {
        type: parsed.type,
        attempt: trace.attempt,
        reason: 'contract_retry',
        at: performance.now(),
      };
    }
    const projected = {
      type: parsed.type,
      attempt: trace.attempt,
      at: performance.now(),
    };
    if (parsed.type === 'run_started') {
      projected.runId = safeDiagnosticToken(parsed.runId, 128) || '';
    }
    if (parsed.type === 'error') {
      projected.code = allowedErrorCodes.has(parsed.code) ? parsed.code : 'LLM_ERROR';
      const diagnostic = projectDiagnostic(parsed.diagnostic);
      if (diagnostic) projected.diagnostic = diagnostic;
    }
    const output = parsed.output;
    if (output && typeof output === 'object') {
      if (typeof output.chat === 'string' && output.chat) {
        projected.chat = summarizeText(output.chat, trace.transient.lastChat, 'chat');
        trace.transient.lastChat = output.chat;
      }
      const markdown = output.artifact_update?.markdown;
      if (typeof markdown === 'string' && markdown) {
        projected.artifact = summarizeText(
          markdown,
          trace.transient.lastArtifact,
          'artifact',
        );
        trace.transient.lastArtifact = markdown;
      }
      projected.requestsNextStage = (
        output.stage_action?.type === 'request_next_stage'
      );
      projected.targetStageId = safeDiagnosticToken(
        output.stage_action?.target_stage_id,
        128,
      );
    }
    return projected;
  };

  window.__ai4seRealStreamTraces = [];
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input.url;
    const response = await originalFetch(input, init);
    if (!url.includes('/api/agent/runs/stream')) return response;

    let request = {};
    try {
      const body = init.body ?? (
        input instanceof Request ? await input.clone().text() : null
      );
      const parsed = body ? JSON.parse(body) : {};
      request = {
        workflowId: safeDiagnosticToken(parsed.workflowId, 64) || '',
        stageId: safeDiagnosticToken(parsed.stageId, 64) || '',
        requestId: safeDiagnosticToken(parsed.requestId, 128) || '',
        runId: safeDiagnosticToken(parsed.runId, 128),
      };
    } catch (_) {
      request = { workflowId: '', stageId: '', requestId: '', runId: null };
    }

    const trace = {
      request,
      status: response.status,
      events: [],
      startedAt: performance.now(),
      done: false,
      observerError: null,
      attempt: 0,
    };
    Object.defineProperty(trace, 'transient', {
      value: { lastChat: '', lastArtifact: '' },
      enumerable: false,
      configurable: true,
    });
    window.__ai4seRealStreamTraces.push(trace);
    const clone = response.clone();
    void (async () => {
      try {
        const reader = clone.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split(/\r?\n\r?\n/);
          buffer = frames.pop() || '';
          for (const frame of frames) {
            const data = frame
              .split(/\r?\n/)
              .filter(line => line.startsWith('data:'))
              .map(line => line.slice(5).trimStart())
              .join('\n');
            if (!data) continue;
            if (data === '[DONE]') {
              trace.events.push({
                type: 'done',
                attempt: trace.attempt,
                at: performance.now(),
              });
              continue;
            }
            trace.events.push(projectEvent(JSON.parse(data), trace));
            queueMicrotask(() => window.__ai4seRealDomSample?.());
          }
        }
        if (buffer.trim()) {
          trace.observerError = 'sse_incomplete_frame';
        }
      } catch (error) {
        trace.observerError = 'sse_observer_failed';
      } finally {
        trace.done = true;
      }
    })();
    return response;
  };
})();
"""


def install_stream_observer(page: Page) -> None:
    page.add_init_script(STREAM_OBSERVER_SCRIPT)


def start_dom_observer(page: Page, stream_index: int) -> None:
    page.evaluate(HASH_TEXT_INSTALL_SCRIPT)
    page.evaluate(
        r"""
        (streamIndex) => {
          const chat = document.querySelector('[data-testid="chat-pane"]');
          const artifact = document.querySelector('[data-testid="artifact-content"]');
          if (!chat || !artifact) throw new Error('functional DOM locators are missing');
          const hashText = window.__ai4seHashText;
          const assistantContent = () => {
            const node = Array.from(
            chat.querySelectorAll('[data-testid="assistant-message-content"]')
            ).at(-1);
            if (!node) return '';
            const clone = node.cloneNode(true);
            clone.querySelectorAll('button').forEach((button) => button.remove());
            return clone.textContent?.trim() || '';
          };
          const assistantSourceSummary = (renderedText) => {
            const node = Array.from(
              chat.querySelectorAll('[data-testid="assistant-message-content"]')
            ).at(-1);
            const hash = node?.getAttribute('data-chat-source-hash') || '';
            const length = Number(node?.getAttribute('data-chat-source-length'));
            if (/^sha256-[0-9a-f]{64}$/.test(hash) && Number.isInteger(length)) {
              return { hash, length };
            }
            return {
              hash: renderedText ? hashText(renderedText) : '',
              length: renderedText.length,
            };
          };
          const currentAssistant = assistantContent();
          const currentAssistantSource = assistantSourceSummary(currentAssistant);
          const currentArtifact = artifact.textContent || '';
          const artifactSourceSummary = (renderedText) => {
            const hash = artifact.getAttribute('data-artifact-source-hash') || '';
            const length = Number(artifact.getAttribute('data-artifact-source-length'));
            if (/^sha256-[0-9a-f]{64}$/.test(hash) && Number.isInteger(length)) {
              return { hash, length };
            }
            return {
              hash: renderedText ? hashText(renderedText) : '',
              length: renderedText.length,
            };
          };
          const currentArtifactSource = artifactSourceSummary(currentArtifact);
          const domArtifactSections = (previousSections = []) => {
            const headingNodes = [...artifact.querySelectorAll('h1,h2,h3,h4,h5,h6')];
            const headingPath = [];
            return headingNodes.map((headingNode) => {
              let text = headingNode.textContent || '';
              let sibling = headingNode.nextElementSibling;
              while (sibling && !/^H[1-6]$/.test(sibling.tagName)) {
                const visualId = sibling.getAttribute('data-artifact-visual-diagnostic-id');
                if (visualId?.startsWith('mermaid:')) {
                  text += `\n[${visualId}]`;
                  sibling = sibling.nextElementSibling;
                  continue;
                }
                const clone = sibling.cloneNode(true);
                clone.querySelectorAll(
                  '[data-artifact-visual-diagnostic-id^="mermaid:"]'
                ).forEach((node) => {
                  const id = node.getAttribute('data-artifact-visual-diagnostic-id');
                  node.replaceWith(document.createTextNode(`[${id}]`));
                });
                clone.querySelectorAll('.mermaid-diagram').forEach((node) => {
                  node.replaceWith(document.createTextNode('[mermaid]'));
                });
                text += `\n${clone.textContent || ''}`;
                sibling = sibling.nextElementSibling;
              }
              const headingLevel = Number(headingNode.tagName.slice(1));
              const heading = `${'#'.repeat(headingLevel)} ${headingNode.textContent || ''}`;
              headingPath.length = Math.max(0, headingLevel - 1);
              headingPath[headingLevel - 1] = heading;
              const headingHash = hashText(headingPath.filter(Boolean).join('\n'));
              const previousSection = previousSections.find(
                (section) => section.headingHash === headingHash
              );
              return {
                headingHash,
                headingLevel,
                metadata: metadataHeadingPattern.test(heading),
                hash: hashText(text),
                length: text.length,
                previousPrefixHash: previousSection
                  ? hashText(text.slice(0, previousSection.length))
                  : null,
              };
            });
          };
          const metadataHeadingPattern = /^#{1,3}\s+(?:\d+\.\s+)?(?:文档|评审|报告)信息$/;
          const sectionMonotonicReason = (before, current) => {
            const businessBefore = before.filter((section) => !section.metadata);
            const businessCurrent = current.filter((section) => !section.metadata);
            const hasDuplicateHeadings = (sections) => (
              new Set(sections.map((section) => section.headingHash)).size
              !== sections.length
            );
            if (
              hasDuplicateHeadings(businessBefore)
              || hasDuplicateHeadings(businessCurrent)
            ) return 'duplicate_heading';
            const isOrderedSubsequence = (expected, actual, matches) => {
              let actualIndex = 0;
              return expected.every((item) => {
                while (
                  actualIndex < actual.length
                  && !matches(item, actual[actualIndex])
                ) {
                  actualIndex += 1;
                }
                if (actualIndex >= actual.length) return false;
                actualIndex += 1;
                return true;
              });
            };
            const headingsRemainOrdered = isOrderedSubsequence(
              businessBefore,
              businessCurrent,
              (previousSection, currentSection) => (
                previousSection.headingHash === currentSection.headingHash
              ),
            );
            const stableSectionsRemainExact = isOrderedSubsequence(
              businessBefore.slice(0, -1),
              businessCurrent,
              (previousSection, currentSection) => (
                previousSection.headingHash === currentSection.headingHash
                && previousSection.hash === currentSection.hash
              ),
            );
            const previousTail = businessBefore.at(-1);
            const currentTail = businessCurrent.find(
              (section) => section.headingHash === previousTail?.headingHash
            );
            const activeTailKeepsPrefix = !previousTail || (
              currentTail?.previousPrefixHash === previousTail.hash
            );
            if (!headingsRemainOrdered) return 'heading_order';
            if (!stableSectionsRemainExact) return 'stable_section_rewrite';
            if (!activeTailKeepsPrefix) return 'active_tail_rewrite';
            return 'ok';
          };
          const state = {
            streamIndex,
            requestId: '',
            events: [],
            attempt: 0,
            lastChat: currentAssistant,
            lastChatSourceHash: currentAssistantSource.hash,
            lastChatSourceLength: currentAssistantSource.length,
            lastArtifact: currentArtifact,
            lastArtifactSourceHash: currentArtifactSource.hash,
            lastArtifactSourceLength: currentArtifactSource.length,
            lastArtifactSections: domArtifactSections(),
            lastChatNetworkIndex: -1,
            seenChat: false,
            seenArtifact: false,
          };
          const summarizeArtifact = (renderedText, source, sections = []) => {
            const networkSummary = (window.__ai4seRealStreamTraces
              ?.at(streamIndex)?.events || [])
              .filter((event) => event.attempt === state.attempt && event.artifact)
              .map((event) => event.artifact)
              .find((summary) => (
                summary.hash === source.hash && summary.length === source.length
            ));
            if (!networkSummary) return null;
            const monotonicReason = !state.seenArtifact
              ? 'ok'
              : sectionMonotonicReason(state.lastArtifactSections, sections);
            const metadataSectionIndex = sections.findIndex(
              (section) => section.metadata
            );
            const metadataSection = metadataSectionIndex >= 0
              ? sections[metadataSectionIndex]
              : null;
            const metadata = networkSummary.metadata && metadataSection
              ? {
                  ...networkSummary.metadata,
                  headingHash: metadataSection.headingHash,
                  headingLevel: metadataSection.headingLevel,
                  index: metadataSectionIndex,
                  isFinal: metadataSectionIndex === sections.length - 1,
                }
              : networkSummary.metadata;
            return {
              length: source.length,
              hash: source.hash,
              previousLength: state.lastArtifactSourceLength,
              previousHash: state.lastArtifactSourceHash || null,
              currentPrefixHash: null,
              renderedLength: renderedText.length,
              renderedHash: renderedText ? hashText(renderedText) : null,
              headings: sections.map((section) => ({
                hash: section.headingHash,
                level: section.headingLevel,
                metadata: section.metadata,
              })),
              sections,
              metadata,
              monotonic: monotonicReason === 'ok',
              monotonicReason,
            };
          };
          const summarizeChat = (renderedText, source) => {
            const placeholderSources = [
              '正在生成...',
              '正在生成...\n\n⚠️ 上下文较长，较早对话已被截断，本轮仅保留最近的对话内容作为模型上下文。',
            ];
            if (placeholderSources.some((placeholder) => (
              placeholder.length === source.length
              && hashText(placeholder) === source.hash
            ))) return null;
            const trace = window.__ai4seRealStreamTraces?.at(streamIndex);
            const indexedChats = (trace?.events || [])
              .map((event, index) => ({ event, index }))
              .filter(({ event }) => (
                event.attempt === state.attempt && event.chat
              ));
            const exactMatches = indexedChats.filter(({ event }) => (
              event.chat.hash === source.hash
              && event.chat.length === source.length
            ));
            const match = exactMatches.find(
              ({ index }) => index >= state.lastChatNetworkIndex
            ) || exactMatches.at(-1);
            const authoritativeChat = trace?.transient?.lastChat || '';
            const sourceMatchesAuthoritative = authoritativeChat
              ? (
                source.length <= authoritativeChat.length
                && hashText(authoritativeChat.slice(0, source.length)) === source.hash
              )
              : Boolean(match);
            const networkIndex = match?.index ?? state.lastChatNetworkIndex;
            let monotonicReason = 'ok';
            if (state.seenChat && source.length < state.lastChatSourceLength) {
              monotonicReason = 'source_length_rewind';
            } else if (!sourceMatchesAuthoritative) {
              monotonicReason = 'source_prefix_rewrite';
            } else if (networkIndex < state.lastChatNetworkIndex) {
              monotonicReason = 'network_order_rewind';
            }
            return {
              length: source.length,
              hash: source.hash,
              previousLength: state.lastChatSourceLength,
              previousHash: state.lastChatSourceHash || null,
              currentPrefixHash: null,
              renderedLength: renderedText.length,
              renderedHash: renderedText ? hashText(renderedText) : null,
              headings: [],
              sections: [],
              metadata: null,
              monotonic: monotonicReason === 'ok',
              monotonicReason,
              networkIndex,
            };
          };
          const sample = () => {
            const trace = window.__ai4seRealStreamTraces?.at(streamIndex);
            if (trace?.request?.requestId) state.requestId = trace.request.requestId;
            const traceAttempt = trace?.attempt || 0;
            if (traceAttempt !== state.attempt) {
              state.attempt = traceAttempt;
              state.lastChatNetworkIndex = -1;
              state.seenChat = false;
              state.seenArtifact = false;
            }
            const assistant = assistantContent();
            const assistantSource = assistantSourceSummary(assistant);
            if (
              assistant
              && assistantSource.hash
              && assistantSource.hash !== state.lastChatSourceHash
            ) {
              const summary = summarizeChat(assistant, assistantSource);
              if (summary) {
                state.events.push({
                  kind: 'chat',
                  attempt: state.attempt,
                  at: performance.now(),
                  ...summary,
                });
                state.lastChat = assistant;
                state.lastChatSourceHash = assistantSource.hash;
                state.lastChatSourceLength = assistantSource.length;
                if (summary.monotonic) {
                  state.lastChatNetworkIndex = summary.networkIndex;
                }
                state.seenChat = true;
              }
            }
            const artifactText = artifact.textContent || '';
            const artifactSource = artifactSourceSummary(artifactText);
            if (
              artifactText
              && artifactSource.hash
              && artifactSource.hash !== state.lastArtifactSourceHash
            ) {
              const sections = domArtifactSections(state.lastArtifactSections);
              const summary = summarizeArtifact(
                artifactText,
                artifactSource,
                sections,
              );
              if (summary) {
                state.events.push({
                  kind: 'artifact',
                  attempt: state.attempt,
                  at: performance.now(),
                  ...summary,
                });
                state.lastArtifact = artifactText;
                state.lastArtifactSourceHash = artifactSource.hash;
                state.lastArtifactSourceLength = artifactSource.length;
                state.lastArtifactSections = sections;
                state.seenArtifact = true;
              }
            }
          };
          const observer = new MutationObserver(sample);
          observer.observe(chat, { childList: true, subtree: true, characterData: true });
          observer.observe(artifact, { childList: true, subtree: true, characterData: true });
          window.__ai4seRealDomState = state;
          window.__ai4seRealDomObserver = observer;
          window.__ai4seRealDomSample = sample;
        }
        """,
        stream_index,
    )


def wait_for_stream_trace(page: Page, index: int, timeout_ms: int) -> dict[str, Any]:
    page.wait_for_function(
        "index => Boolean(window.__ai4seRealStreamTraces?.[index]?.done)",
        arg=index,
        timeout=timeout_ms,
    )
    return page.evaluate(
        "index => window.__ai4seRealStreamTraces[index]",
        index,
    )


def finish_dom_observer(page: Page) -> dict[str, Any]:
    return page.evaluate(r"""
        () => {
          window.__ai4seRealDomSample?.();
          window.__ai4seRealDomObserver?.disconnect();
          const state = window.__ai4seRealDomState;
          const trace = window.__ai4seRealStreamTraces?.at(state?.streamIndex);
          const result = {
            requestId: state?.requestId || '',
            streamIndex: state?.streamIndex,
            events: state?.events || [],
          };
          if (state) {
            delete state.lastChat;
            delete state.lastChatSourceHash;
            delete state.lastChatSourceLength;
            delete state.lastArtifact;
            delete state.lastArtifactSourceHash;
            delete state.lastArtifactSourceLength;
            delete state.lastArtifactSections;
            delete state.lastChatNetworkIndex;
          }
          if (trace) delete trace.transient;
          return result;
        }
        """)


def latest_trace_summary(page: Page | None) -> dict[str, Any]:
    if page is None:
        return {}
    try:
        return page.evaluate(r"""
            () => {
              const trace = window.__ai4seRealStreamTraces?.at(-1);
              if (!trace) return {};
              const lastArtifact = [...trace.events]
                .reverse()
                .find((event) => event.artifact)?.artifact;
              const diagnostic = [...trace.events]
                .reverse()
                .find((event) => event.type === 'error')?.diagnostic || null;
              return {
                runId: trace.events.find((event) => event.type === 'run_started')?.runId || null,
                workflowId: trace.request?.workflowId || null,
                stageId: trace.request?.stageId || null,
                requestId: trace.request?.requestId || null,
                eventTypes: trace.events.map((event) => event.type),
                retryCount: trace.events.filter((event) => event.type === 'agent_retry').length,
                artifactHash: lastArtifact?.hash || null,
                observerError: trace.observerError,
                diagnostic,
              };
            }
            """)
    except PlaywrightError:
        return {}
