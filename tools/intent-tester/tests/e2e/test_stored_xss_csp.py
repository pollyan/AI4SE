from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import requests


PAYLOAD_MARKER = "intent-e2e-xss-marker"
SCRIPT_PAYLOAD = (
    "</script><script>window.__intentXss=1;"
    "fetch('/intent-e2e-exfil?via=script')</script>"
)
HTML_PAYLOAD = (
    '<img src=x onerror="window.__intentXss=2;'
    "fetch('/intent-e2e-exfil?via=img')\">"
    '<svg onload="window.__intentXss=3"></svg>'
    '<a href="javascript:window.__intentXss=4" onclick="window.__intentXss=5">x</a>'
)


def _login(page, base_url: str) -> None:
    observed_origin = []

    def record_login_post(request) -> None:
        if request.method == "POST" and request.url.startswith(
            f"{base_url}/intent-tester/login"
        ):
            observed_origin.append(request.headers.get("origin"))

    page.on("request", record_login_post)
    response = page.goto(f"{base_url}/intent-tester/login")
    assert response and response.status == 200
    page.locator('input[name="username"]').fill("admin")
    page.locator('input[name="password"]').fill("e2e-admin-password")
    page.locator('button[type="submit"]').click()
    assert re.search(r"/intent-tester/testcases$", page.url), {
        "url": page.url,
        "origin": observed_origin,
        "body": page.locator("body").inner_text(),
    }


def _create_testcase(page, payload: dict) -> dict:
    result = page.evaluate(
        """async (payload) => {
            const token = document.querySelector('meta[name="intent-csrf-token"]').content;
            const response = await fetch('/intent-tester/api/testcases', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token},
                body: JSON.stringify(payload)
            });
            return {status: response.status, body: await response.json()};
        }""",
        payload,
    )
    assert result["status"] == 200, result
    assert result["body"]["code"] == 200, result
    return result["body"]["data"]


def _assert_strict_csp(response) -> str:
    csp = response.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "script-src-attr 'none'" in csp
    assert "style-src-attr 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp
    assert "*" not in csp
    match = re.search(r"script-src 'self' 'nonce-([^']+)'", csp)
    assert match, csp
    return match.group(1)


def _assert_safe_page(page, nonce: str) -> None:
    assert page.evaluate("window.__intentXss") == 0
    assert page.locator("[onerror], [onload], [onclick]").count() == 0
    assert page.locator('a[href^="javascript:"]').count() == 0
    inline_nonces = page.locator("script:not([src]), style").evaluate_all(
        "elements => elements.map(element => element.nonce)"
    )
    assert inline_nonces
    assert set(inline_nonces) == {nonce}


def test_operator_stored_payload_is_text_under_real_chromium_csp(
    restricted_server, chromium_browser
) -> None:
    context = chromium_browser.new_context()
    context.set_default_timeout(5_000)
    context.set_default_navigation_timeout(10_000)
    page = context.new_page()
    page.add_init_script(
        """window.__intentXss = 0;
        window.__intentCspViolations = [];
        document.addEventListener('securitypolicyviolation', event => {
            window.__intentCspViolations.push({directive: event.violatedDirective});
        });"""
    )
    dialogs = []
    exploit_requests = []
    external_requests = []
    page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

    def record_request(request) -> None:
        parsed = urlparse(request.url)
        if "/intent-e2e-exfil" in parsed.path:
            exploit_requests.append(request.url)
        if parsed.scheme in {"http", "https"} and parsed.hostname not in {
            "127.0.0.1",
            "localhost",
        }:
            external_requests.append(request.url)

    page.on("request", record_request)
    try:
        _login(page, restricted_server.base_url)
        payload = {
            "name": f"{PAYLOAD_MARKER} {HTML_PAYLOAD}",
            "description": f"description {SCRIPT_PAYLOAD} attribute=' autofocus",
            "category": f"security {HTML_PAYLOAD}",
            "priority": 1,
            "tags": ["xss", "csp"],
            "steps": [
                {
                    "action": "aiQuery",
                    "description": f"step {SCRIPT_PAYLOAD} {HTML_PAYLOAD}",
                    "params": {
                        "locate": HTML_PAYLOAD,
                        "query": SCRIPT_PAYLOAD,
                        "schema": HTML_PAYLOAD,
                        "url": "javascript:window.__intentXss=6",
                        "report_path": "../../intent-e2e-exfil/report.html",
                    },
                    "output_variable": f"value-{HTML_PAYLOAD}",
                }
            ],
        }
        created = _create_testcase(page, payload)
        testcase_id = created["id"]
        assert created["name"] == payload["name"]
        assert created["steps"][0]["params"]["report_path"].startswith("../..")

        responses = []
        responses.append(page.goto(f"{restricted_server.base_url}/intent-tester/testcases"))
        page.get_by_text(payload["name"], exact=True).wait_for()
        list_nonce = _assert_strict_csp(responses[-1])
        _assert_safe_page(page, list_nonce)

        responses.append(
            page.goto(
                f"{restricted_server.base_url}/intent-tester/testcases/{testcase_id}/edit"
            )
        )
        edit_nonce = _assert_strict_csp(responses[-1])
        assert edit_nonce != list_nonce
        assert page.locator("#testcase-name").input_value() == payload["name"]
        assert page.locator("#testcase-description").input_value() == payload[
            "description"
        ]
        page.locator("#testcase-description").fill(payload["description"] + " edited")
        assert page.locator("#testcase-description").input_value().endswith(" edited")
        page.locator(".step-edit").click()
        assert page.locator("#edit-title-0").input_value() == payload["steps"][0][
            "description"
        ]
        assert page.locator("#edit-action-0").input_value() == "aiQuery"
        assert json.loads(page.locator("#edit-params-0").input_value()) == payload[
            "steps"
        ][0]["params"]
        assert page.locator("#edit-output-variable-0").input_value() == payload[
            "steps"
        ][0]["output_variable"]
        page.locator("#edit-title-0").fill(payload["steps"][0]["description"] + " edited")
        edited_params = payload["steps"][0]["params"] | {
            "locate": payload["steps"][0]["params"]["locate"] + " edited"
        }
        page.locator("#edit-params-0").fill(json.dumps(edited_params))
        page.locator("#edit-output-variable-0").fill("safe_e2e_output")
        page.locator(".save-step-inline").click()
        with page.expect_response(
            lambda candidate: candidate.request.method == "PUT"
            and candidate.url.endswith(f"/intent-tester/api/testcases/{testcase_id}")
        ) as save_info:
            page.locator("#save-testcase").click()
        assert save_info.value.status == 200

        persisted = page.evaluate(
            """async (testcaseId) => {
                const response = await fetch(`/intent-tester/api/testcases/${testcaseId}`);
                return response.json();
            }""",
            testcase_id,
        )
        assert persisted["data"]["description"].endswith(" edited")
        assert persisted["data"]["steps"][0]["description"].endswith(" edited")
        assert persisted["data"]["steps"][0]["params"] == edited_params
        assert persisted["data"]["steps"][0]["output_variable"] == "safe_e2e_output"
        _assert_safe_page(page, edit_nonce)

        responses.append(
            page.goto(
                f"{restricted_server.base_url}/intent-tester/execution?testcase_id={testcase_id}"
            )
        )
        execution_nonce = _assert_strict_csp(responses[-1])
        selected_option = page.locator(
            f'#testcase-select option[value="{testcase_id}"]'
        )
        selected_option.wait_for(state="attached")
        assert selected_option.text_content() == payload["name"]
        assert page.locator("#start-execution").is_visible()
        assert page.locator("#start-execution").is_enabled()
        page.locator("#testcase-select").select_option(str(testcase_id))
        with page.expect_response(
            lambda candidate: candidate.request.method == "POST"
            and candidate.url.endswith("/intent-tester/api/executions")
        ) as create_execution_info:
            page.locator("#start-execution").click()
        assert create_execution_info.value.status == 502
        page.wait_for_function(
            "new URL(window.location.href).searchParams.has('execution_id')"
        )
        assert page.locator("#retry-execution").is_visible()
        _assert_safe_page(page, execution_nonce)

        responses.append(
            page.goto(f"{restricted_server.base_url}/intent-tester/local-proxy")
        )
        local_proxy_nonce = _assert_strict_csp(responses[-1])
        assert page.locator("#connection-status").count() == 1
        _assert_safe_page(page, local_proxy_nonce)

        csrf = page.locator('meta[name="intent-csrf-token"]').get_attribute("content")
        cookie_header = "; ".join(
            f"{cookie['name']}={cookie['value']}" for cookie in context.cookies()
        )
        rejected = requests.post(
            f"{restricted_server.base_url}/intent-tester/api/testcases",
            json={"name": "foreign-origin"},
            headers={
                "Origin": "https://foreign.example",
                "X-CSRF-Token": csrf,
                "Cookie": cookie_header,
            },
            timeout=2,
        )
        assert rejected.status_code == 403
        assert rejected.json()["error"]["code"] == "ORIGIN_REJECTED"

        assert page.evaluate("window.__intentXss") == 0
        assert exploit_requests == []
        assert dialogs == []
        assert external_requests == []
    finally:
        context.close()


def test_public_readonly_anonymous_cannot_open_detail_or_mutate(
    public_readonly_server, chromium_browser
) -> None:
    admin_context = chromium_browser.new_context()
    admin_context.set_default_timeout(5_000)
    admin_context.set_default_navigation_timeout(10_000)
    admin_page = admin_context.new_page()
    try:
        _login(admin_page, public_readonly_server.base_url)
        created = _create_testcase(
            admin_page,
            {
                "name": "public safe summary",
                "description": "summary only",
                "category": "security",
                "steps": [
                    {
                        "action": "goto",
                        "description": "private step",
                        "params": {"url": "https://private.example"},
                    }
                ],
            },
        )
    finally:
        admin_context.close()

    anonymous = chromium_browser.new_context()
    anonymous.set_default_timeout(5_000)
    anonymous.set_default_navigation_timeout(10_000)
    page = anonymous.new_page()
    try:
        list_response = page.goto(
            f"{public_readonly_server.base_url}/intent-tester/testcases"
        )
        assert list_response and list_response.status == 200
        page.get_by_text("public safe summary", exact=True).wait_for()

        summary = requests.get(
            f"{public_readonly_server.base_url}/intent-tester/api/testcases",
            timeout=2,
        )
        assert summary.status_code == 200
        item = summary.json()["data"]["items"][0]
        assert item["id"] == created["id"]
        assert "steps" not in item
        assert "created_by" not in item

        edit = page.goto(
            f"{public_readonly_server.base_url}/intent-tester/testcases/{created['id']}/edit"
        )
        assert edit and edit.status == 403
        mutation = requests.post(
            f"{public_readonly_server.base_url}/intent-tester/api/testcases",
            json={"name": "forbidden"},
            headers={"Origin": public_readonly_server.base_url},
            timeout=2,
        )
        assert mutation.status_code == 403
        assert mutation.json()["error"]["code"] == "READ_ONLY_MODE"
    finally:
        anonymous.close()
