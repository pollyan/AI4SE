from __future__ import annotations

import json
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e


WORKFLOW_PROBES = (
    ("TEST_DESIGN", "CLARIFY", "lisa", "test-design", "需求分析文档"),
    ("REQ_REVIEW", "REVIEW", "lisa", "req-review", "需求评审问题清单"),
    ("INCIDENT_REVIEW", "TIMELINE", "lisa", "incident-review", "故障复盘报告"),
    ("IDEA_BRAINSTORM", "DEFINE", "alex", "idea-brainstorm", "问题域分析"),
    ("VALUE_DISCOVERY", "ELEVATOR", "alex", "value-discovery", "价值定位分析"),
    ("STORY_BREAKDOWN", "INPUT_ANALYSIS", "alex", "story-breakdown", "用户故事拆解包"),
    ("PRD_REVIEW", "INVENTORY", "alex", "prd-review", "PRD 输入盘点"),
)


def _artifact(title: str, count: int) -> str:
    lines = [f"# {title}"]
    for index in range(1, count + 1):
        lines.extend(("", f"## 渐进章节 {index}", "", f"QG018-ARTIFACT-{index}"))
    return "\n".join(lines)


def _install_timed_stream_fetch(
    page: Page,
    title: str,
) -> None:
    chat = "我已完成当前阶段判断，接下来会按段落逐步更新右侧产出物。"
    artifacts = [_artifact(title, count) for count in (1, 2, 3)]
    events = [
        {"type": "run_started", "runId": "qg018-browser-run"},
        {
            "type": "agent_delta",
            "output": {"chat": chat, "warnings": []},
        },
        *(
            {
                "type": "agent_delta",
                "output": {
                    "artifact_update": {"type": "replace", "markdown": artifact},
                    "warnings": [],
                },
            }
            for artifact in artifacts[:2]
        ),
        {
            "type": "agent_turn",
            "output": {
                "chat": chat,
                "artifact_update": {"type": "replace", "markdown": artifacts[2]},
                "stage_action": None,
                "warnings": [],
            },
        },
    ]
    events_json = json.dumps(events, ensure_ascii=False)
    page.add_init_script(script=r"""
        (() => {
          const events = __QG018_EVENTS__;
          const chunks = [
            ...events.map((event) => `data: ${JSON.stringify(event)}\n\n`),
            'data: [DONE]\n\n',
          ];
          const originalFetch = window.fetch.bind(window);
          window.__qg018FetchInstalled = true;
          window.__qg018FetchUrls = [];
          window.fetch = async (input, init = {}) => {
            const url = typeof input === 'string' ? input : input.url;
            window.__qg018FetchUrls.push(url);
            if (!url.includes('/api/agent/runs/stream')) {
              return originalFetch(input, init);
            }
            const body = init.body ?? (
              input instanceof Request ? await input.clone().text() : null
            );
            window.__qg018StreamRequest = body ? JSON.parse(body) : {};
            const encoder = new TextEncoder();
            const stream = new ReadableStream({
              start(controller) {
                let index = 0;
                const enqueueNext = () => {
                  controller.enqueue(encoder.encode(chunks[index]));
                  index += 1;
                  if (index < chunks.length) {
                    window.setTimeout(enqueueNext, 100);
                  } else {
                    window.setTimeout(() => controller.close(), 100);
                  }
                };
                window.setTimeout(enqueueNext, 100);
              },
            });
            return new Response(stream, {
              status: 200,
              headers: { 'Content-Type': 'text/event-stream' },
            });
          };
        })();
        """.replace("__QG018_EVENTS__", events_json))


def _start_dom_commit_observer(page: Page) -> None:
    page.evaluate("""
        () => {
          const chatPane = document.querySelector('[data-testid="chat-pane"]');
          const artifact = document.querySelector('[data-testid="artifact-content"]');
          if (!chatPane || !artifact) {
            throw new Error('QG018 observer requires ChatPane and ArtifactPane');
          }
          const initialAssistant = Array.from(
            chatPane.querySelectorAll('[data-testid="assistant-message-content"]')
          ).at(-1)?.textContent || '';
          const state = {
            events: [],
            artifactStates: [],
            chatSeen: false,
            lastArtifactText: artifact.textContent || '',
          };
          const sample = () => {
            const assistant = Array.from(
              chatPane.querySelectorAll('[data-testid="assistant-message-content"]')
            ).at(-1)?.textContent || '';
            if (
              !state.chatSeen
              && assistant !== initialAssistant
              && assistant.includes('按段落逐步更新右侧产出物')
            ) {
              state.events.push('chat');
              state.chatSeen = true;
            }
            const artifactText = artifact.textContent || '';
            if (artifactText === state.lastArtifactText) return;
            state.lastArtifactText = artifactText;
            if (!artifactText.includes('QG018-ARTIFACT-1')) return;
            state.artifactStates.push(artifactText);
            if (artifactText.includes('QG018-ARTIFACT-3')) {
              state.events.push('final');
            } else if (artifactText.includes('QG018-ARTIFACT-2')) {
              state.events.push('artifact-2');
            } else {
              state.events.push('artifact-1');
            }
          };
          const observer = new MutationObserver(sample);
          observer.observe(chatPane, { childList: true, subtree: true, characterData: true });
          observer.observe(artifact, { childList: true, subtree: true, characterData: true });
          window.__qg018DomCommitState = state;
          window.__qg018DomCommitObserver = observer;
        }
        """)


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "agent_id", "slug", "title"),
    WORKFLOW_PROBES,
)
def test_all_workflows_commit_chat_then_three_artifact_states_in_headless_chromium(
    new_agents_page: Page,
    new_agents_base_url: str,
    workflow_id: str,
    stage_id: str,
    agent_id: str,
    slug: str,
    title: str,
) -> None:
    _install_timed_stream_fetch(new_agents_page, title)
    workspace_url = urljoin(
        new_agents_base_url,
        f"workspace/{agent_id}/{slug}",
    )
    new_agents_page.goto(
        workspace_url,
        wait_until="domcontentloaded",
        timeout=60_000,
    )
    new_agents_page.locator("textarea").wait_for(timeout=30_000)
    new_agents_page.get_by_test_id("artifact-content").wait_for(timeout=30_000)
    _start_dom_commit_observer(new_agents_page)

    new_agents_page.locator("textarea").fill("请生成当前阶段产出物")
    new_agents_page.locator("#send-button").click()
    new_agents_page.wait_for_function(
        """() => window.__qg018DomCommitState?.events.length >= 4""",
        timeout=10_000,
    )

    result = new_agents_page.evaluate("""
        () => {
          window.__qg018DomCommitObserver?.disconnect();
          return {
            events: [...window.__qg018DomCommitState.events],
            artifactStates: [...window.__qg018DomCommitState.artifactStates],
            request: window.__qg018StreamRequest,
            fetchInstalled: window.__qg018FetchInstalled,
            fetchUrls: [...(window.__qg018FetchUrls || [])],
            assistantText: Array.from(
              document.querySelectorAll('[data-testid="assistant-message-content"]')
            ).at(-1)?.textContent || '',
            artifactText: document.querySelector(
              '[data-testid="artifact-content"]'
            )?.textContent || '',
          };
        }
        """)

    assert result["fetchInstalled"] is True, result
    assert result["fetchUrls"].count("/new-agents/api/agent/runs/stream") == 1, result
    assert result["request"] is not None, result
    assert result["events"] == ["chat", "artifact-1", "artifact-2", "final"], result
    assert len(result["artifactStates"]) == 3
    assert len(set(result["artifactStates"])) == 3
    marker_sets = [
        {index for index in range(1, 4) if f"QG018-ARTIFACT-{index}" in artifact_state}
        for artifact_state in result["artifactStates"]
    ]
    assert marker_sets == [{1}, {1, 2}, {1, 2, 3}]
    expected_final_text = "".join(
        [title]
        + [
            value
            for index in range(1, 4)
            for value in (f"渐进章节 {index}", f"QG018-ARTIFACT-{index}")
        ]
    )
    assert "".join(result["artifactStates"][-1].split()) == "".join(
        expected_final_text.split()
    )
    assert result["request"]["workflowId"] == workflow_id
    assert result["request"]["stageId"] == stage_id
