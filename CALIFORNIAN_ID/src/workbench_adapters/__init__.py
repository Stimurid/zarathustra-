"""Branch adapters for the Tinkuy Workbench.

Each adapter MAY import ``workbench_core`` plus its own branch runtime.
``workbench_core`` MAY NOT import any of them.

    zarathustra_adapter  -> workbench_core + californian_id.zarathustra   (live)
    socrates_adapter     -> workbench_core + socrates.*                   (pending
                            materialisation of 07_SOCRATES_PIPELINE_PACK)
"""
from .socrates_adapter import SocratesBranchAdapter
from .whitecrow_projection import WhiteCrowProjectionAdapter
from .zarathustra_adapter import ZarathustraAdapter

__all__ = ["ZarathustraAdapter", "WhiteCrowProjectionAdapter",
           "SocratesBranchAdapter"]
