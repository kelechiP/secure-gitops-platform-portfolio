locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Repository  = "kelechiP/secure-gitops-platform-portfolio"
    },
    var.additional_tags
  )

  subnet_count = length(var.availability_zones)
  nat_count = var.nat_gateway_strategy == "none" ? 0 : (
    var.nat_gateway_strategy == "single" ? 1 : local.subnet_count
  )
}
