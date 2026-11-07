"""Keep the current dependency inventory aligned with executable inputs."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class DependencyInventoryTests(unittest.TestCase):
    def test_current_action_inventory_matches_every_workflow_reference(self):
        document = (ROOT / "docs/supply-chain-security.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| `([^`]+/[^`]+)` \| (v[0-9.]+) \| `([0-9a-f]{40})` \|", document, re.MULTILINE)
        inventory = {name: (version, sha) for name, version, sha in rows}
        self.assertTrue(inventory)
        self.assertEqual(len(rows), len(inventory))
        used = set()
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            for name, sha, version in re.findall(
                    r"uses: ([\w-]+/[\w-]+)@([0-9a-f]{40}) # (v[0-9.]+)",
                    path.read_text(encoding="utf-8")):
                with self.subTest(workflow=path.name, action=name):
                    self.assertEqual(inventory.get(name), (version, sha))
                used.add(name)
        self.assertEqual(used, set(inventory))

    def test_current_base_inventory_matches_dockerfile(self):
        dockerfile = (ROOT / "app/Dockerfile").read_text(encoding="utf-8")
        digest = re.search(r"^FROM gcr\.io/distroless/python3-debian13:nonroot@(sha256:[0-9a-f]{64})$",
                           dockerfile, re.MULTILINE)
        self.assertIsNotNone(digest)
        document = (ROOT / "docs/supply-chain-security.md").read_text(encoding="utf-8")
        current = document.split("## Current Distroless base pin", 1)[1].split("### Historical release boundary", 1)[0]
        digests = re.findall(r"sha256:[0-9a-f]{64}", current)
        self.assertEqual(len(digests), 2)  # Index and platform child, not historical inputs.
        self.assertEqual(digests[0], digest.group(1))
        for user in re.findall(r"^USER (.+)$", dockerfile, re.MULTILINE):
            self.assertIn(user, ("nonroot", "65532", "nonroot:nonroot", "65532:65532"))
        self.assertIn("COPY --chown=nonroot:nonroot", dockerfile)

    def test_pr_workflow_has_no_release_authority_or_publication(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("pull_request:", ci)
        self.assertNotIn("pull_request_target:", ci)
        self.assertNotRegex(ci, r"(?m)^\s+[\w-]+:\s*(?:write|write-all)\s*$")
        self.assertNotRegex(ci, r"(?m)^\s*permissions:\s*write-all")
        for forbidden in ("id-token:", "attestations:", "push: true", "docker push",
                          "docker/login-action@", "actions/attest", "cosign sign"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, ci)
        self.assertIn("push: false", ci)


if __name__ == "__main__":
    unittest.main()
