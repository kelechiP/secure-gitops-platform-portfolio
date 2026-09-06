import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "release.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_release_resolves_tag_commit_and_requires_main_ancestry(self):
        required_fragments = (
            "fetch-depth: 0",
            "set -euo pipefail",
            'git rev-parse --verify "${GITHUB_SHA}^{commit}"',
            "git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main",
            'git merge-base --is-ancestor "${release_commit}" refs/remotes/origin/main',
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.workflow)

    def test_ancestry_gate_precedes_privileged_release_operations(self):
        ancestry = self.workflow.index("git merge-base --is-ancestor")
        for operation in ("Log in to GHCR", "docker push", "Attest build provenance", "cosign sign"):
            with self.subTest(operation=operation):
                self.assertLess(ancestry, self.workflow.index(operation))


if __name__ == "__main__":
    unittest.main()
