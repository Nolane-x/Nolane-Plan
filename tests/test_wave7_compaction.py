from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel


class Wave7CompactionTests(unittest.TestCase):
    def test_kernel_exposes_reversible_compaction_api(self):
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "compact safely")
        self.assertTrue(hasattr(kernel, "compact_lineage"))
        self.assertTrue(hasattr(kernel, "reconstruct_compacted_lineage"))


if __name__ == "__main__":
    unittest.main()
