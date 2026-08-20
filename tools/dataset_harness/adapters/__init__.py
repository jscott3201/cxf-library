"""Dataset adapter registry."""

from .lbl_fpu import LblFpuAdapter

ADAPTERS = {LblFpuAdapter.slug: LblFpuAdapter}

__all__ = ["ADAPTERS", "LblFpuAdapter"]
