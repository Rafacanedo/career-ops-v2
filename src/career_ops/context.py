"""
context.py — Shared Click context object.

Extracted to a separate module to break the circular import between
cli.py (which imports the command modules) and the command modules
(which need pass_ctx / CareerOpsContext).
"""

from __future__ import annotations

import click

from .config import get_db_path, resolve_root
from .repository import CareerOpsRepository


class CareerOpsContext:
    def __init__(self, root_str: str | None) -> None:
        self.root = resolve_root(root_str)
        self.db_path = get_db_path(self.root)
        self._repository: CareerOpsRepository | None = None

    @property
    def repository(self) -> CareerOpsRepository:
        if self._repository is None:
            self._repository = CareerOpsRepository(db_path=self.db_path, auto_init=True)
        return self._repository

    @property
    def repo(self) -> CareerOpsRepository:
        return self.repository


pass_ctx = click.make_pass_decorator(CareerOpsContext)
