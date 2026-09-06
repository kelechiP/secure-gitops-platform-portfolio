import re
import unittest
from pathlib import Path


EKS_TF = (
    Path(__file__).resolve().parents[2] / "infra" / "terraform" / "aws" / "eks.tf"
)


def resource_body(configuration: str, resource_type: str, name: str) -> str:
    marker = f'resource "{resource_type}" "{name}" {{'
    body = configuration.split(marker, 1)[1]
    depth = 1
    for index, character in enumerate(body):
        depth += character == "{"
        depth -= character == "}"
        if depth == 0:
            return body[:index]
    raise AssertionError(f"Unclosed resource: {resource_type}.{name}")


class TerraformNodeSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configuration = EKS_TF.read_text(encoding="utf-8")
        cls.template = resource_body(configuration, "aws_launch_template", "eks_nodes")
        cls.node_group = resource_body(configuration, "aws_eks_node_group", "this")

    def test_launch_template_enforces_root_volume_and_metadata_security(self):
        for setting in (
            r'device_name\s*=\s*"/dev/xvda"',
            r"encrypted\s*=\s*true",
            r'volume_type\s*=\s*"gp3"',
            r"volume_size\s*=\s*var\.node_disk_size_gib",
            r"delete_on_termination\s*=\s*true",
            r'http_tokens\s*=\s*"required"',
            r"http_put_response_hop_limit\s*=\s*2",
        ):
            self.assertRegex(self.template, setting)

    def test_node_group_uses_latest_launch_template_without_disk_size(self):
        self.assertRegex(
            self.node_group, r"id\s*=\s*aws_launch_template\.eks_nodes\.id"
        )
        self.assertRegex(
            self.node_group,
            r"version\s*=\s*aws_launch_template\.eks_nodes\.latest_version",
        )
        self.assertNotRegex(self.node_group, r"(?m)^\s*disk_size\s*=")


if __name__ == "__main__":
    unittest.main()
