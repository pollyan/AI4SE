from sse_response import build_sse_response
from sse_schemas import ErrorEvent


def test_build_sse_response_encodes_events_and_done_sentinel() -> None:
    response = build_sse_response([
        ErrorEvent(code="STREAM_ERROR", message="failed"),
    ])

    assert response.mimetype == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["X-Accel-Buffering"] == "no"
    assert response.get_data(as_text=True) == (
        'data: {"type": "error", "code": "STREAM_ERROR", "message": "failed"}\n\n'
        "data: [DONE]\n\n"
    )
