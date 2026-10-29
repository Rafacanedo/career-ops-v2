"""
context.py — Shared Click context object.

Extracted to a separate module to break the circular import between
cli.py (which imports the command modules) and the command modules
(which need pass_ctx / CareerOpsContext).
"""

from __future__ import annotations

import click

from .config import resolve_root


class CareerOpsContext:
    def __init__(self, root_str: str | None):
        self.root = resolve_root(root_str)


pass_ctx = click.make_pass_decorator(CareerOpsContext)
