"""Participant adapters — one per engine.

Each adapter turns a real runtime into something the Arena can hand a case
to. The Arena knows the adapter interface (:class:`ParticipantAdapter`) and
nothing about the engine underneath.
"""
from __future__ import annotations

from .baseline import BaselineSingleAgent
from .zarathustra import ZarathustraParticipant

__all__ = ["BaselineSingleAgent", "ZarathustraParticipant"]
