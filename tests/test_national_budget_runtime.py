"""Run offline national-budget runtime regressions with Node's built-in runner."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NationalBudgetRuntimeTests(unittest.TestCase):
    def test_node_runtime(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required for national-budget runtime checks")
        result = subprocess.run(
            [node, "--test", str(ROOT / "tests/national-budget-runtime.cjs")],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
