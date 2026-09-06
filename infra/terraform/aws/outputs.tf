output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs used for controlled ingress and NAT gateways."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs used by EKS nodes and the control plane."
  value       = aws_subnet.private[*].id
}

output "cluster_name" {
  description = "EKS cluster name."
  value       = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  description = "EKS API endpoint."
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64-encoded EKS cluster CA data."
  value       = aws_eks_cluster.this.certificate_authority[0].data
  sensitive   = true
}

output "node_group_name" {
  description = "Managed node group name."
  value       = aws_eks_node_group.this.node_group_name
}

output "eks_secrets_kms_key_arn" {
  description = "KMS key ARN used for Kubernetes secrets envelope encryption."
  value       = aws_kms_key.eks_secrets.arn
}

output "nat_gateway_ids" {
  description = "NAT gateway IDs; empty when nat_gateway_strategy is none."
  value       = aws_nat_gateway.this[*].id
}
