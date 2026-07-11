"""Contracts for Intent Tester's strict CSP and routed-page DOM safety."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


INTENT_TESTER_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ROOT = INTENT_TESTER_ROOT / "frontend" / "templates"
STATIC_ROOT = INTENT_TESTER_ROOT / "frontend" / "static"
ROUTED_TEMPLATES = {
    "base_layout.html",
    "testcases.html",
    "testcase_edit.html",
    "execution.html",
    "local_proxy.html",
    "login.html",
}
ROUTED_PAGE_SCRIPTS = {
    "js/button-protection.js",
    "js/components/EnhancedStepEditor.js",
    "js/config/variableFieldConfig.js",
    "js/durable-execution-control.js",
    "js/enhanced-editor-controller.js",
    "js/intent-security.js",
    "js/list-components.js",
    "js/safe-dom.js",
    "js/services/VariableContextService.js",
    "js/smart-variable-input.js",
    "js/utils/variableValidation.js",
}


def _executable_inline_scripts(source: str) -> list[str]:
    scripts: list[str] = []
    for attributes, body in re.findall(
        r"<script\b([^>]*)>(.*?)</script>", source, flags=re.IGNORECASE | re.DOTALL
    ):
        if re.search(r"\bsrc\s*=", attributes, flags=re.IGNORECASE):
            continue
        if re.search(
            r"\btype\s*=\s*['\"]application/json['\"]",
            attributes,
            flags=re.IGNORECASE,
        ):
            continue
        scripts.append(body)
    return scripts


def _remote_resource_violations(source: str) -> list[str]:
    violations: list[str] = []
    for tag_name, attributes in re.findall(
        r"<(script|link)\b([^>]*)>", source, flags=re.IGNORECASE
    ):
        if tag_name.lower() == "script":
            match = re.search(r"\bsrc\s*=\s*['\"]([^'\"]+)", attributes, re.I)
        elif re.search(r"\brel\s*=\s*['\"][^'\"]*stylesheet", attributes, re.I):
            match = re.search(r"\bhref\s*=\s*['\"]([^'\"]+)", attributes, re.I)
        else:
            match = None
        if match and re.match(r"(?:https?:)?//", match.group(1), flags=re.I):
            violations.append(match.group(1))
    return violations


def _event_property_assignments(source: str) -> list[str]:
    return re.findall(r"\.(on[a-z]+)\s*=", source)


def _unsafe_url_assignments(source: str) -> list[str]:
    safe_names = set(
        re.findall(
            r"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*IntentSafeDom\.safeUrl\s*\(",
            source,
        )
    )
    assignments = re.findall(
        r"(?:\.(?:href|src)\s*=\s*|setAttribute\s*\(\s*['\"](?:href|src)['\"]\s*,\s*)"
        r"([^;\n)]+(?:\([^;\n]*\))?)",
        source,
        flags=re.IGNORECASE,
    )
    assignments.extend(
        re.findall(
            r"(?:window\.)?location\.assign\s*\(\s*([^)]+)\)",
            source,
        )
    )
    unsafe: list[str] = []
    for raw_expression in assignments:
        expression = raw_expression.strip().rstrip(")").strip()
        quoted_literal = re.fullmatch(
            r"(['\"])(?:\\.|(?!\1).)*\1",
            expression,
            flags=re.DOTALL,
        )
        if quoted_literal:
            continue
        if expression.startswith("IntentSafeDom.safeUrl("):
            continue
        if expression in safe_names:
            continue
        unsafe.append(expression)
    return unsafe


def _unsafe_fetches_without_shared_csrf(source: str) -> list[str]:
    violations: list[str] = []
    for match in re.finditer(
        r"fetch\s*\([^,]+,\s*\{(?P<options>.*?)\n\s*\}\s*\)",
        source,
        flags=re.DOTALL,
    ):
        options = match.group("options")
        method_match = re.search(
            r"\bmethod\s*:\s*(?P<method>['\"](?:POST|PUT|PATCH|DELETE)['\"]|[A-Za-z_$][\w$]*)",
            options,
            flags=re.IGNORECASE,
        )
        if method_match is None:
            continue
        method = method_match.group("method")
        helper = rf"IntentSecurity\.csrfHeaders\s*\(\s*{re.escape(method)}\s*\)"
        if not re.search(helper, options):
            violations.append(method)
    return violations


def _derived_routed_page_scripts() -> set[str]:
    paths: set[str] = set()
    for template_name in ROUTED_TEMPLATES:
        source = (TEMPLATE_ROOT / template_name).read_text(encoding="utf-8")
        paths.update(
            re.findall(
                r"url_for\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"]([^'\"]+\.js)['\"]",
                source,
            )
        )
        paths.update(re.findall(r"\bsrc=['\"]/static/([^'\"]+\.js)['\"]", source))
    return {path for path in paths if not path.startswith("vendor/")}


def _parse_csp(value: str) -> dict[str, list[str]]:
    directives: dict[str, list[str]] = {}
    for raw_directive in value.split(";"):
        parts = raw_directive.strip().split()
        if parts:
            directives[parts[0]] = parts[1:]
    return directives


def _inline_blocks(source: str) -> list[tuple[str, str]]:
    return re.findall(r"<(script|style)\b([^>]*)>", source, flags=re.IGNORECASE)


def _unsafe_inner_html_assignments(source: str) -> list[str]:
    assignments = re.findall(
        r"\.innerHTML\s*=\s*(.*?);(?=\s*(?:\n|$))", source, flags=re.DOTALL
    )
    unsafe: list[str] = []
    for expression in assignments:
        candidate = expression.strip()
        if re.search(r"\{[{%#]", candidate):
            unsafe.append(candidate)
            continue
        quoted_literal = re.fullmatch(r"(['\"])(?:\\.|(?!\1).)*\1", candidate, re.DOTALL)
        template_literal = re.fullmatch(r"`(?:\\.|[^`])*`", candidate, re.DOTALL)
        if quoted_literal:
            continue
        if template_literal and "${" not in candidate:
            continue
        unsafe.append(candidate)
    return unsafe


def test_inner_html_contract_only_allows_compile_time_literals():
    assert _unsafe_inner_html_assignments("node.innerHTML = '';") == []
    assert _unsafe_inner_html_assignments("node.innerHTML = `<b>ready</b>`;") == []
    assert _unsafe_inner_html_assignments("node.innerHTML = value;") == ["value"]
    assert _unsafe_inner_html_assignments("node.innerHTML = `<b>${value}</b>`;") == [
        "`<b>${value}</b>`"
    ]


def test_inner_html_contract_rejects_jinja_runtime_interpolation():
    assignment = "node.innerHTML = '{{ testcase.name }}';"

    assert _unsafe_inner_html_assignments(assignment) == ["'{{ testcase.name }}'"]


def test_resource_scanner_rejects_any_remote_script_or_stylesheet():
    fixture = """
        <script src="https://assets.example.test/app.js"></script>
        <link rel="stylesheet" href="//styles.example.test/app.css">
        <img src="https://images.example.test/allowed-by-img-policy.png">
    """

    assert _remote_resource_violations(fixture) == [
        "https://assets.example.test/app.js",
        "//styles.example.test/app.css",
    ]


def test_event_property_scanner_catches_lowercase_dom_events_only():
    fixture = """
        node.onpointerdown = handler;
        node.ondragstart = handler;
        node.onanimationend = handler;
        controller.onParameterChange = callback;
    """

    assert _event_property_assignments(fixture) == [
        "onpointerdown",
        "ondragstart",
        "onanimationend",
    ]


def test_url_sink_scanner_requires_safe_url_for_dynamic_values():
    unsafe = """
        anchor.href = report.path;
        image.src = screenshot.path;
        anchor.setAttribute('href', runtimeValue);
        window.location.assign(runtimeTarget);
        anchor.href = '/reports/' + report.path;
        image.src = "/screenshots/" + screenshot.path;
        anchor.setAttribute('href', '/go/' + runtimeValue);
        window.location.assign('/go/' + runtimeTarget);
    """
    safe = """
        anchor.href = '/reports/static.html';
        window.location.assign('/intent-tester/testcases');
        const safeReportUrl = IntentSafeDom.safeUrl(report.path, ['https:']);
        anchor.href = safeReportUrl;
        window.location.assign(safeReportUrl);
    """

    assert len(_unsafe_url_assignments(unsafe)) == 8
    assert _unsafe_url_assignments(safe) == []


def test_routed_script_scan_is_mechanically_derived_from_templates():
    assert _derived_routed_page_scripts() == ROUTED_PAGE_SCRIPTS


def test_fetch_scanner_requires_shared_csrf_for_unsafe_methods_only():
    unsafe = """
        fetch('/intent-tester/api/testcases', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
    """
    safe = """
        fetch('/intent-tester/api/testcases', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...IntentSecurity.csrfHeaders('PUT')
            }
        })
    """
    readonly = "fetch('/intent-tester/api/testcases')"

    assert _unsafe_fetches_without_shared_csrf(unsafe) == ["'POST'"]
    assert _unsafe_fetches_without_shared_csrf(safe) == []
    assert _unsafe_fetches_without_shared_csrf(readonly) == []


def test_routed_pages_have_strict_nonce_csp(operator_client):
    response = operator_client.get("/intent-tester/testcases")

    assert response.status_code == 200
    csp = response.headers["Content-Security-Policy"]
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp
    assert "*" not in csp
    assert "upgrade-insecure-requests" not in csp

    nonce_match = re.search(r"'nonce-([^']+)'", csp)
    assert nonce_match is not None
    nonce = nonce_match.group(1)
    assert re.fullmatch(r"[A-Za-z0-9_-]{32}", nonce)

    directives = _parse_csp(csp)
    assert directives == {
        "default-src": ["'none'"],
        "script-src": ["'self'", f"'nonce-{nonce}'"],
        "script-src-attr": ["'none'"],
        "style-src": ["'self'", f"'nonce-{nonce}'"],
        "style-src-attr": ["'none'"],
        "object-src": ["'none'"],
        "base-uri": ["'none'"],
        "frame-ancestors": ["'none'"],
        "form-action": ["'self'"],
        "connect-src": ["'self'", "http://localhost:3001", "ws://localhost:3001"],
        "img-src": ["'self'", "data:"],
        "font-src": ["'self'"],
    }
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), geolocation=(), microphone=()"
    )


def test_csp_nonce_is_fresh_per_request_and_matches_inline_blocks(operator_client):
    first = operator_client.get("/intent-tester/testcases")
    second = operator_client.get("/intent-tester/testcases")
    first_nonce = re.search(
        r"'nonce-([^']+)'", first.headers["Content-Security-Policy"]
    ).group(1)
    second_nonce = re.search(
        r"'nonce-([^']+)'", second.headers["Content-Security-Policy"]
    ).group(1)

    assert first_nonce != second_nonce
    for response, nonce in ((first, first_nonce), (second, second_nonce)):
        for tag_name, attributes in _inline_blocks(response.get_data(as_text=True)):
            if tag_name.lower() == "script" and re.search(r"\bsrc\s*=", attributes):
                continue
            assert re.search(
                rf'\bnonce=["\']{re.escape(nonce)}["\']', attributes
            ), attributes


@pytest.mark.parametrize(
    "path",
    (
        "/intent-tester/testcases",
        "/intent-tester/testcases/create",
        "/intent-tester/execution",
        "/intent-tester/local-proxy",
        "/intent-tester/login",
    ),
)
def test_each_routed_page_renders_only_current_nonce_inline_blocks(
    operator_client, path
):
    response = operator_client.get(path)

    assert response.status_code == 200
    nonce = re.search(
        r"'nonce-([^']+)'", response.headers["Content-Security-Policy"]
    ).group(1)
    for tag_name, attributes in _inline_blocks(response.get_data(as_text=True)):
        if tag_name.lower() == "script" and re.search(r"\bsrc\s*=", attributes):
            continue
        assert re.search(
            rf'\bnonce=["\']{re.escape(nonce)}["\']', attributes
        ), attributes


@pytest.mark.filterwarnings(
    "ignore:datetime.datetime.utcnow.*:DeprecationWarning:sqlalchemy.sql.schema"
)
@pytest.mark.filterwarnings(
    "ignore:The Query.get\\(\\) method is considered legacy.*:sqlalchemy.exc.LegacyAPIWarning:flask_sqlalchemy.query"
)
def test_existing_testcase_data_stays_out_of_executable_script_source(
    db_session, operator_client
):
    from backend.models import TestCase

    testcase_id = 730019
    marker = "</script><script>window.__persisted_xss = true</script>"
    testcase = TestCase(
        id=testcase_id,
        name=marker,
        description=marker,
        steps=json.dumps(
            [{"action": "ai", "description": marker, "params": {"prompt": marker}}]
        ),
        category=marker,
        priority=2,
        tags="review",
        created_by="operator",
    )
    db_session.add(testcase)
    db_session.commit()

    response = operator_client.get(f"/intent-tester/testcases/{testcase_id}/edit")
    html = response.get_data(as_text=True)
    executable_source = "\n".join(_executable_inline_scripts(html))

    assert response.status_code == 200
    assert str(testcase_id) not in executable_source
    assert marker not in executable_source
    data_match = re.search(
        r'<script id="intent-testcase-data"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    assert data_match is not None
    data = json.loads(data_match.group(1))
    assert data["testcaseId"] == testcase_id
    assert marker in json.loads(data["stepsJson"])[0]["description"]


def test_routed_templates_have_no_inline_attributes_cdns_or_safe_filter():
    violations: list[str] = []
    for template_name in sorted(ROUTED_TEMPLATES):
        source = (TEMPLATE_ROOT / template_name).read_text(encoding="utf-8")
        checks = {
            "inline handler": r"\son[a-z]+\s*=",
            "inline style": r"\sstyle\s*=",
            "CDN URL": r"https?://(?:unpkg\.com|cdn(?:\.socket\.io|js\.com|\.jsdelivr\.net))",
            "safe filter": r"\|\s*safe\b",
        }
        for label, pattern in checks.items():
            if re.search(pattern, source, flags=re.IGNORECASE):
                violations.append(f"{template_name}: {label}")

        for tag_name, attributes in _inline_blocks(source):
            if tag_name.lower() == "script" and re.search(r"\bsrc\s*=", attributes):
                continue
            if 'nonce="{{ csp_nonce }}"' not in attributes:
                violations.append(f"{template_name}: unnonced inline {tag_name}")
        if _remote_resource_violations(source):
            violations.append(f"{template_name}: remote script or stylesheet")

    assert violations == []


def test_routed_sources_reject_runtime_html_and_event_property_sinks():
    violations: list[str] = []
    sources = {
        f"templates/{name}": (TEMPLATE_ROOT / name).read_text(encoding="utf-8")
        for name in ROUTED_TEMPLATES
    }
    sources.update(
        {
            f"static/{name}": (STATIC_ROOT / name).read_text(encoding="utf-8")
            for name in _derived_routed_page_scripts()
        }
    )

    for name, source in sorted(sources.items()):
        unsafe_assignments = _unsafe_inner_html_assignments(source)
        if unsafe_assignments:
            violations.append(f"{name}: runtime innerHTML")
        for label, pattern in {
            "insertAdjacentHTML": r"\.insertAdjacentHTML\s*\(",
            "outerHTML": r"\.outerHTML\s*=",
            "style attribute": r"setAttribute\s*\(\s*['\"]style['\"]",
            "javascript URL": r"['\"]javascript\s*:",
            "file URL": r"['\"]file\s*:",
        }.items():
            if re.search(pattern, source, flags=re.IGNORECASE):
                violations.append(f"{name}: {label}")
        if _event_property_assignments(source):
            violations.append(f"{name}: event property")
        if _unsafe_url_assignments(source):
            violations.append(f"{name}: unsafe URL assignment")

    assert violations == []


def test_routed_unsafe_fetches_use_shared_csrf_headers():
    sources = {
        f"templates/{name}": (TEMPLATE_ROOT / name).read_text(encoding="utf-8")
        for name in ROUTED_TEMPLATES
    }
    sources.update(
        {
            f"static/{name}": (STATIC_ROOT / name).read_text(encoding="utf-8")
            for name in _derived_routed_page_scripts()
        }
    )

    violations = {
        name: methods
        for name, source in sources.items()
        if (methods := _unsafe_fetches_without_shared_csrf(source))
    }

    assert violations == {}


def test_local_vendor_assets_match_locked_browser_clients():
    lock = json.loads((INTENT_TESTER_ROOT / "package-lock.json").read_text())
    expected = {
        "axios": ("1.13.2", "axios/dist/axios.min.js", "axios-1.13.2.min.js"),
        "socket.io-client": (
            "4.8.1",
            "socket.io-client/dist/socket.io.min.js",
            "socket.io-client-4.8.1.min.js",
        ),
    }

    for package, (version, installed_path, vendor_name) in expected.items():
        assert lock["packages"][f"node_modules/{package}"]["version"] == version
        installed = INTENT_TESTER_ROOT / "node_modules" / installed_path
        vendored = STATIC_ROOT / "vendor" / vendor_name
        assert vendored.read_bytes() == installed.read_bytes()

    base_layout = (TEMPLATE_ROOT / "base_layout.html").read_text(encoding="utf-8")
    assert "url_for('static', filename='vendor/axios-1.13.2.min.js')" in base_layout
    assert "url_for('static', filename='vendor/socket.io-client-4.8.1.min.js')" in base_layout


def test_browser_security_helpers_publish_narrow_interfaces():
    intent_security = (STATIC_ROOT / "js" / "intent-security.js").read_text()
    safe_dom = (STATIC_ROOT / "js" / "safe-dom.js").read_text()

    assert "window.IntentSecurity" in intent_security
    assert "csrfHeaders" in intent_security
    assert "GET" in intent_security
    assert "HEAD" in intent_security
    assert "OPTIONS" in intent_security
    assert "X-CSRF-Token" in intent_security
    assert "window.IntentSafeDom" in safe_dom
    for method in ("text", "button", "safeUrl", "replaceChildren"):
        assert re.search(rf"\b{method}\b", safe_dom)
    assert "textContent" in safe_dom
    assert "addEventListener" in safe_dom
    assert "replaceChildren" in safe_dom
