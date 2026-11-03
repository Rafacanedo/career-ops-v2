"""
Schemas package for Career-Ops v2.
"""

from .cv import ContactInfo, CVPayload, EducationEntry, ProjectEntry, WorkRole
from .eval import EvaluationPayload

__all__ = [
    "ContactInfo",
    "CVPayload",
    "EducationEntry",
    "ProjectEntry",
    "WorkRole",
    "EvaluationPayload",
]
