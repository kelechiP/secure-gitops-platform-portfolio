import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_action_pins import strip_yaml_comment, validate_reference, validate_workflow


SHA = "0123456789abcdef0123456789abcdef01234567"
DIGEST = "a" * 64


class ActionPinValidationTests(unittest.TestCase):
    def test_accepts_full_commit_with_version_comment(self):
        self.assertIsNone(validate_reference(f"actions/checkout@{SHA}"))
        self.assertEqual(
            strip_yaml_comment(f"actions/checkout@{SHA} # v7.0.1"),
            f"actions/checkout@{SHA}",
        )

    def test_accepts_local_action(self):
        self.assertIsNone(validate_reference("./.github/actions/test"))

    def test_accepts_digest_pinned_docker_action(self):
        self.assertIsNone(validate_reference(f"docker://alpine@sha256:{DIGEST}"))

    def test_rejects_mutable_remote_action(self):
        self.assertIsNotNone(validate_reference("actions/checkout@v7"))

    def test_rejects_mutable_reusable_workflow(self):
        self.assertIsNotNone(validate_reference("owner/repository/.github/workflows/build.yml@main"))

    def test_rejects_tagged_docker_action(self):
        self.assertIsNotNone(validate_reference("docker://alpine:3.22"))

    def test_scans_step_and_job_level_uses_with_quoted_scalars(self):
        workflow = f"""jobs:
  call:
    uses: 'owner/repository/.github/workflows/build.yml@{SHA}' # v1.2.3
  local:
    steps:
      - uses: "./.github/actions/test"
      - uses: docker://alpine@sha256:{DIGEST}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_text(workflow, encoding="utf-8")
            self.assertEqual(validate_workflow(path), [])


if __name__ == "__main__":
    unittest.main()
