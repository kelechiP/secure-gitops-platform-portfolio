variable "aws_region" {
  description = "AWS Region for the development foundation."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project identifier used in resource names and tags."
  type        = string
  default     = "secure-gitops"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.project_name))
    error_message = "project_name must be 3-31 lowercase alphanumeric or hyphen characters and start with a letter."
  }
}

variable "environment" {
  description = "Environment identifier used in names and tags."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,15}$", var.environment))
    error_message = "environment must be 2-16 lowercase alphanumeric or hyphen characters and start with a letter."
  }
}

variable "availability_zones" {
  description = "Availability zones used for public and private subnets."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]

  validation {
    condition     = length(var.availability_zones) >= 2 && length(distinct(var.availability_zones)) == length(var.availability_zones)
    error_message = "Provide at least two unique availability zones."
  }
}

variable "vpc_cidr" {
  description = "IPv4 CIDR for the VPC."
  type        = string
  default     = "10.40.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 CIDR."
  }
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs, one per availability zone."
  type        = list(string)
  default     = ["10.40.0.0/24", "10.40.1.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) >= 2 && alltrue([for cidr in var.public_subnet_cidrs : can(cidrnetmask(cidr))])
    error_message = "Provide at least two valid public IPv4 subnet CIDRs."
  }
}

variable "private_subnet_cidrs" {
  description = "Private worker subnet CIDRs, one per availability zone."
  type        = list(string)
  default     = ["10.40.10.0/24", "10.40.11.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) >= 2 && alltrue([for cidr in var.private_subnet_cidrs : can(cidrnetmask(cidr))])
    error_message = "Provide at least two valid private IPv4 subnet CIDRs."
  }
}

variable "nat_gateway_strategy" {
  description = "NAT strategy: single for lower-cost development, one_per_az for resilience, or none when private endpoints are supplied separately."
  type        = string
  default     = "single"

  validation {
    condition     = contains(["single", "one_per_az", "none"], var.nat_gateway_strategy)
    error_message = "nat_gateway_strategy must be single, one_per_az, or none."
  }
}

variable "cluster_version" {
  description = "Kubernetes minor version for EKS. Review AWS support before deployment."
  type        = string
  default     = "1.34"

  validation {
    condition     = can(regex("^1\\.[0-9]{2}$", var.cluster_version))
    error_message = "cluster_version must use a Kubernetes minor version such as 1.34."
  }
}

variable "cluster_endpoint_public_access" {
  description = "Whether the EKS API endpoint is reachable publicly. Private access remains enabled."
  type        = bool
  default     = false
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "Restricted CIDRs allowed to reach the public EKS API endpoint when enabled."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.cluster_endpoint_public_access_cidrs :
      can(cidrnetmask(cidr)) && cidr != "0.0.0.0/0"
    ])
    error_message = "Public endpoint CIDRs must be valid and must not include 0.0.0.0/0."
  }
}

variable "cluster_admin_principal_arn" {
  description = "Optional IAM principal ARN granted EKS cluster-admin access through an EKS access entry."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.cluster_admin_principal_arn == null || can(regex("^arn:aws:iam::[0-9]{12}:(role|user)/.+$", var.cluster_admin_principal_arn))
    error_message = "cluster_admin_principal_arn must be null or a valid IAM role/user ARN."
  }
}

variable "node_instance_types" {
  description = "EC2 instance types allowed for the managed node group."
  type        = list(string)
  default     = ["t3.small"]
}

variable "node_capacity_type" {
  description = "Managed node group capacity type. SPOT lowers development cost; ON_DEMAND is steadier."
  type        = string
  default     = "SPOT"

  validation {
    condition     = contains(["SPOT", "ON_DEMAND"], var.node_capacity_type)
    error_message = "node_capacity_type must be SPOT or ON_DEMAND."
  }
}

variable "node_min_size" {
  description = "Minimum managed node count."
  type        = number
  default     = 1
}

variable "node_desired_size" {
  description = "Desired managed node count."
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum managed node count."
  type        = number
  default     = 2
}

variable "node_disk_size_gib" {
  description = "Encrypted root volume size for each managed node."
  type        = number
  default     = 20
}

variable "control_plane_log_retention_days" {
  description = "CloudWatch retention for EKS control-plane logs."
  type        = number
  default     = 30
}

variable "additional_tags" {
  description = "Additional non-sensitive tags applied by the AWS provider."
  type        = map(string)
  default     = {}
}
