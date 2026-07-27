"""Adapter for Markdown output of a "units of content" cutter.

Handles two flavours of the same format:
- rich: preamble with source audit (участники, дефекты диаризации, OCR)
  followed by `### Un — Title` sections;
- lean: straight `### Un — Title` list with a passport per unit.

Zero LLM — pure regex + markdown structure. No enrichment, no invention.
"""
from .parser import parse_md_units_file, parse_md_units_text

__all__ = ["parse_md_units_file", "parse_md_units_text"]
