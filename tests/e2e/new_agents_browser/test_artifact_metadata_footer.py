from __future__ import annotations

import json
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.e2e


WORKFLOW_PROBES = (
    (
        "TEST_DESIGN",
        "CLARIFY",
        "lisa",
        "test-design",
        None,
        "需求分析文档",
        "文档信息",
    ),
    (
        "REQ_REVIEW",
        "REVIEW",
        "lisa",
        "req-review",
        None,
        "需求评审问题清单",
        "评审信息",
    ),
    (
        "INCIDENT_REVIEW",
        "IMPROVEMENT",
        "lisa",
        "incident-review",
        "改进报告",
        "故障复盘报告",
        "报告信息",
    ),
    (
        "IDEA_BRAINSTORM",
        "DEFINE",
        "alex",
        "idea-brainstorm",
        None,
        "问题域分析",
        None,
    ),
    (
        "VALUE_DISCOVERY",
        "ELEVATOR",
        "alex",
        "value-discovery",
        None,
        "价值定位分析",
        "文档信息",
    ),
    (
        "STORY_BREAKDOWN",
        "INPUT_ANALYSIS",
        "alex",
        "story-breakdown",
        None,
        "用户故事拆解包",
        "文档信息",
    ),
    (
        "PRD_REVIEW",
        "INVENTORY",
        "alex",
        "prd-review",
        None,
        "PRD 输入盘点",
        "文档信息",
    ),
)


def _long_artifact(title: str, footer_heading: str | None) -> str:
    lines = [f"# {title}"]
    for index in range(1, 25):
        lines.extend(
            (
                "",
                f"## 业务章节 {index}",
                "",
                f"QG019-BUSINESS-{index:02d}：这是用于验证长文档滚动和正文优先展示的业务结论。",
            )
        )
    if footer_heading:
        lines.extend(
            (
                "",
                f"## {footer_heading}",
                "",
                "文档元信息：Artifact 名称：QG019 验证产物 ｜ Workflow：当前工作流 ｜ Stage：当前阶段 ｜ 状态：已完成",
            )
        )
    return "\n".join(lines)


def _install_metadata_stream_fetch(
    page: Page,
    title: str,
    footer_heading: str | None,
) -> None:
    chat = "业务分析已经完成，详细内容已在右侧产出物中展示。"
    artifact = _long_artifact(title, footer_heading)
    events = [
        {"type": "run_started", "runId": "qg019-browser-run"},
        {"type": "agent_delta", "output": {"chat": chat, "warnings": []}},
        {
            "type": "agent_turn",
            "output": {
                "chat": chat,
                "artifact_update": {"type": "replace", "markdown": artifact},
                "stage_action": None,
                "warnings": [],
            },
        },
    ]
    events_json = json.dumps(events, ensure_ascii=False)
    page.add_init_script(script=r"""
        (() => {
          const events = __QG019_EVENTS__;
          const chunks = [
            ...events.map((event) => `data: ${JSON.stringify(event)}\n\n`),
            'data: [DONE]\n\n',
          ];
          const originalFetch = window.fetch.bind(window);
          window.fetch = async (input, init = {}) => {
            const url = typeof input === 'string' ? input : input.url;
            if (!url.includes('/api/agent/runs/stream')) {
              return originalFetch(input, init);
            }
            const body = init.body ?? (
              input instanceof Request ? await input.clone().text() : null
            );
            window.__qg019StreamRequest = body ? JSON.parse(body) : {};
            const encoder = new TextEncoder();
            const stream = new ReadableStream({
              start(controller) {
                chunks.forEach((chunk, index) => {
                  window.setTimeout(() => {
                    controller.enqueue(encoder.encode(chunk));
                    if (index === chunks.length - 1) controller.close();
                  }, 80 * (index + 1));
                });
              },
            });
            return new Response(stream, {
              status: 200,
              headers: { 'Content-Type': 'text/event-stream' },
            });
          };
        })();
        """.replace("__QG019_EVENTS__", events_json))


@pytest.mark.parametrize(
    (
        "workflow_id",
        "stage_id",
        "agent_id",
        "slug",
        "stage_tab",
        "title",
        "footer_heading",
    ),
    WORKFLOW_PROBES,
)
def test_all_workflows_keep_compact_metadata_at_the_end_of_a_long_artifact(
    new_agents_page: Page,
    new_agents_base_url: str,
    workflow_id: str,
    stage_id: str,
    agent_id: str,
    slug: str,
    stage_tab: str | None,
    title: str,
    footer_heading: str | None,
) -> None:
    new_agents_page.set_viewport_size({"width": 1024, "height": 800})
    _install_metadata_stream_fetch(new_agents_page, title, footer_heading)
    new_agents_page.goto(
        urljoin(new_agents_base_url, f"workspace/{agent_id}/{slug}"),
        wait_until="domcontentloaded",
        timeout=60_000,
    )
    new_agents_page.locator("textarea").wait_for(timeout=30_000)
    artifact = new_agents_page.get_by_test_id("artifact-content")
    artifact.wait_for(timeout=30_000)

    if stage_tab:
        new_agents_page.locator("header").get_by_text(stage_tab, exact=True).click()

    new_agents_page.locator("textarea").fill("请生成当前阶段长文档")
    new_agents_page.locator("#send-button").click()
    artifact.get_by_text("QG019-BUSINESS-24", exact=False).wait_for(timeout=10_000)

    request = new_agents_page.evaluate("() => window.__qg019StreamRequest")
    assert request["workflowId"] == workflow_id
    assert request["stageId"] == stage_id

    layout = artifact.evaluate("""
        (node) => {
          const scroller = node.parentElement;
          const first = Array.from(node.querySelectorAll('p')).find(
            (element) => element.textContent?.includes('QG019-BUSINESS-01')
          );
          const last = Array.from(node.querySelectorAll('p')).find(
            (element) => element.textContent?.includes('QG019-BUSINESS-24')
          );
          if (!scroller || !first || !last) throw new Error('missing long artifact nodes');
          const scrollerRect = scroller.getBoundingClientRect();
          const isInsideScroller = (element) => {
            const rect = element.getBoundingClientRect();
            return rect.top >= scrollerRect.top && rect.bottom <= scrollerRect.bottom;
          };
          return {
            scrollHeight: scroller.scrollHeight,
            clientHeight: scroller.clientHeight,
            firstInViewport: isInsideScroller(first),
            lastInViewport: isInsideScroller(last),
          };
        }
        """)
    assert layout["scrollHeight"] > layout["clientHeight"], layout
    assert layout["firstInViewport"] is True, layout
    assert layout["lastInViewport"] is False, layout

    if footer_heading is None:
        assert artifact.get_by_text("文档元信息：", exact=False).count() == 0
        return

    footer = artifact.locator("h2", has_text=footer_heading)
    footer.wait_for(timeout=10_000)
    footer_state = footer.evaluate("""
        (heading) => {
          const artifact = heading.closest('[data-testid="artifact-content"]');
          const scroller = artifact?.parentElement;
          const first = Array.from(artifact?.querySelectorAll('p') || []).find(
            (element) => element.textContent?.includes('QG019-BUSINESS-01')
          );
          const metadata = heading.nextElementSibling;
          if (!artifact || !scroller || !first || !metadata) {
            throw new Error('missing metadata footer nodes');
          }
          const scrollerRect = scroller.getBoundingClientRect();
          const footerRect = heading.getBoundingClientRect();
          return {
            orderIsCorrect: Boolean(
              first.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING
            ),
            initiallyInViewport: (
              footerRect.top >= scrollerRect.top && footerRect.bottom <= scrollerRect.bottom
            ),
            metadataText: metadata.textContent || '',
            metadataTag: metadata.tagName,
            tableCount: artifact.querySelectorAll('table').length,
          };
        }
        """)
    assert footer_state["orderIsCorrect"] is True, footer_state
    assert footer_state["initiallyInViewport"] is False, footer_state
    assert footer_state["metadataTag"] == "P", footer_state
    assert footer_state["metadataText"].startswith("文档元信息："), footer_state
    assert footer_state["tableCount"] == 0, footer_state

    footer.scroll_into_view_if_needed()
    assert footer.evaluate("""
        (heading) => {
          const scroller = heading.closest('[data-testid="artifact-content"]')?.parentElement;
          if (!scroller) return false;
          const scrollerRect = scroller.getBoundingClientRect();
          const footerRect = heading.getBoundingClientRect();
          return footerRect.top >= scrollerRect.top && footerRect.bottom <= scrollerRect.bottom;
        }
        """) is True
