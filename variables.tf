# ============================================
# variables.tf - All Input Variables
# ============================================

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-north-1" 
}

variable "instance_type" {
  description = "EC2 instance type — t3.micro is Free Tier eligible"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Name of your AWS EC2 Key Pair for SSH access"
  type        = string
}

variable "repo_url" {
  description = "Your GitHub repo URL"
  type        = string
  default     = "https://github.com/tomasayman60-cmd/online-course-website-"
}

variable "tags" {
  description = "Default tags for all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    ManagedBy   = "Terraform"
    Project     = "ECourses"
  }
}