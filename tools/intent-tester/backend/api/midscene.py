"""Retired MidScene callback surface.

Durable execution lifecycle writes are accepted only through
``executions.record_execution_lifecycle``.
"""

from flask import Blueprint


midscene_bp = Blueprint("midscene", __name__)


__all__ = ["midscene_bp"]
