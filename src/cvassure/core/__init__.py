"""CVAssure core: schema, contracts, pipeline. Heavy libraries never import here."""

from __future__ import annotations

__version__ = "0.1.0"

from cvassure.core.finding import Finding, draft_schema, final_schema

__all__ = ["Finding", "__version__", "draft_schema", "final_schema"]
