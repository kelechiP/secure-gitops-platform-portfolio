terraform {
  required_version = ">= 1.11.0, < 1.16.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.61"
    }
  }

  backend "s3" {}
}
