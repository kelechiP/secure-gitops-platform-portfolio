resource "aws_security_group" "eks_control_plane" {
  name_prefix = "${local.name_prefix}-eks-control-plane-"
  description = "Additional EKS control-plane security group with no inbound rules"
  vpc_id      = aws_vpc.this.id

  egress {
    description = "Control plane traffic to resources inside the VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${local.name_prefix}-eks-control-plane"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_kms_key" "eks_secrets" {
  description             = "Envelope encryption for ${local.name_prefix} Kubernetes secrets"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  tags = {
    Name = "${local.name_prefix}-eks-secrets"
  }
}

resource "aws_kms_alias" "eks_secrets" {
  name          = "alias/${local.name_prefix}-eks-secrets"
  target_key_id = aws_kms_key.eks_secrets.key_id
}

resource "aws_cloudwatch_log_group" "eks_control_plane" {
  name              = "/aws/eks/${local.name_prefix}/cluster"
  retention_in_days = var.control_plane_log_retention_days

  tags = {
    Name = "${local.name_prefix}-eks-control-plane-logs"
  }
}
