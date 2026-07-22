provider "aws" {
  region = "ap-south-1"
}

resource "aws_ecr_repository" "ai_platform" {
  name                 = "digipay-ai-platform"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "ai-platform-redis"
  engine               = "redis"
  node_type            = "cache.t3.medium"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}
