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

    def test_only_version_tag_pushes_can_release(self):
        trigger = self.workflow.split("on:\n", 1)[1].split("\nconcurrency:", 1)[0]
        self.assertEqual(trigger.strip(), 'push:\n    tags:\n      - "v*.*.*"')
        self.assertIn(r'^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$', self.workflow)

    def test_repository_wide_concurrency_preserves_running_release(self):
        concurrency = self.workflow.split("concurrency:\n", 1)[1].split("\nenv:", 1)[0]
        self.assertEqual(concurrency.strip(),
                         "group: release-${{ github.repository }}\n  cancel-in-progress: false")

    def test_guard_and_inventory_gate_all_publication(self):
        guard = self.workflow.index("run: python3 scripts/check_release_tag.py")
        for operation in ("docker/setup-buildx-action@", "docker/build-push-action@",
                          "Log in to GHCR", "docker push", "Attest build provenance",
                          "Attest SPDX SBOM", "cosign sign", "cosign verify"):
            with self.subTest(operation=operation):
                self.assertLess(guard, self.workflow.index(operation))
        stages = ("Build release image", "Scan before publication", "Generate SPDX SBOM before publication",
                  "Validate generated SPDX SBOM", "Log in to GHCR", "Push scanned image")
        positions = [self.workflow.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(self.workflow.count("uses: docker/build-push-action@"), 1)
        self.assertNotIn(":latest", self.workflow)
        self.assertIn('assert sbom["packages"]', self.workflow)
        self.assertIn('assert sbom["spdxVersion"].startswith("SPDX-2.")', self.workflow)

    def test_permissions_and_digest_based_evidence_are_preserved(self):
        pre_jobs, jobs = self.workflow.split("jobs:\n", 1)
        self.assertEqual(pre_jobs.split("permissions:\n", 1)[1].strip(), "contents: read")
        for permission in ("packages: write", "id-token: write", "attestations: write"):
            self.assertIn(permission, jobs)
        self.assertEqual(jobs.count("subject-digest: ${{ steps.publish.outputs.digest }}"), 2)
        self.assertEqual(jobs.count("DIGEST: ${{ steps.publish.outputs.digest }}"), 2)
        self.assertIn('cosign sign --yes "${IMAGE}@${DIGEST}"', jobs)
        self.assertIn('--certificate-identity "https://github.com/${GITHUB_WORKFLOW_REF}"', jobs)
        self.assertIn('"${IMAGE}@${DIGEST}"', jobs)


if __name__ == "__main__":
    unittest.main()
