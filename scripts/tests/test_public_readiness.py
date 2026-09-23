import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PublicReadinessTests(unittest.TestCase):
    def test_official_nonroot_base_requires_full_digest(self):
        dockerfile = (ROOT / "app/Dockerfile").read_text(encoding="utf-8")
        bases = re.findall(r"^FROM (.+)$", dockerfile, re.MULTILINE)
        self.assertEqual(len(bases), 1)
        self.assertRegex(bases[0], r"^gcr\.io/distroless/python3-debian13:nonroot@sha256:[0-9a-f]{64}$")
        self.assertIn("COPY --chown=nonroot:nonroot", dockerfile)

    def test_guard_precedes_build_and_push_with_existing_token(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        guard = workflow.index("run: python3 scripts/check_release_tag.py")
        for operation in ("docker/setup-buildx-action@", "docker/build-push-action@", "docker push"):
            self.assertLess(guard, workflow.index(operation))
        self.assertIn("group: release-${{ github.repository }}", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        section = workflow[workflow.index("- name: Refuse an existing"):guard]
        self.assertIn("GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}", section)
        self.assertIn("${{ env.IMAGE }}:${{ github.sha }}", workflow)

    def test_artifact_retention_preserves_scan_failure_evidence(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        for workflow in (ci, release):
            self.assertIn("DOCKER_BUILD_RECORD_RETENTION_DAYS: 7", workflow)
            self.assertIn("retention-days: 7", workflow)
        self.assertIn('GITLEAKS_ENABLE_UPLOAD_ARTIFACT: "false"', ci)
        self.assertIn("always() && hashFiles('results.sarif') != ''", ci)
        self.assertIn("path: results.sarif", ci)
        self.assertNotIn("continue-on-error:", ci)


if __name__ == "__main__":
    unittest.main()
