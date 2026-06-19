from collections.abc import Iterable

from flask import Response, has_request_context, stream_with_context

from sse_encoder import encode_sse_done, encode_sse_event
from sse_schemas import SseEvent


def build_sse_response(events: Iterable[SseEvent]) -> Response:
    def generate():
        for event in events:
            yield encode_sse_event(event)
        yield encode_sse_done()

    stream = generate()
    if has_request_context():
        stream = stream_with_context(stream)

    return Response(
        stream,
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
