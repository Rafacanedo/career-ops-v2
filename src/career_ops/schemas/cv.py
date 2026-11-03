from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    email: str
    phone: Optional[str] = None
    location: str
    linkedin_url: str
    portfolio_url: Optional[str] = None


class WorkRole(BaseModel):
    company: str
    role: str
    location: str
    start_date: str
    end_date: str
    bullets: List[str] = Field(..., max_length=8)


class EducationEntry(BaseModel):
    institution: str
    degree: str
    year: str
    location: Optional[str] = None
    details: Optional[str] = None


class ProjectEntry(BaseModel):
    name: str
    description: str
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class CVPayload(BaseModel):
    format: Literal["a4", "letter"] = "a4"
    lang: Literal["en", "pt-br"] = "en"
    name: str = Field(..., max_length=100)
    headline: str = Field(..., max_length=120)
    contact: ContactInfo
    summary: str = Field(..., max_length=650)
    experience: List[WorkRole] = Field(..., max_length=4)
    skills: Dict[str, List[str]]
    education: List[EducationEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
