# Terraform skeleton: AWS ECS Fargate behind an ALB (not applied in tests/CI).
terraform { required_providers { aws = { source = "hashicorp/aws" version = "~> 5.0" } } }
variable "region" { default = "us-east-1" }
variable "image" { default = "markets-agent-platform:latest" }
provider "aws" { region = var.region }

resource "aws_ecs_cluster" "main" { name = "markets-agent-platform" }
resource "aws_vpc" "main" { cidr_block = "10.0.0.0/16" }
resource "aws_subnet" "a" { vpc_id = aws_vpc.main.id cidr_block = "10.0.1.0/24" availability_zone = "${var.region}a" }
resource "aws_security_group" "app" {
  vpc_id = aws_vpc.main.id
  ingress { from_port = 8000 to_port = 8000 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] } # ponytail: tighten to ALB SG in prod
  egress  { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
}
resource "aws_ecs_task_definition" "app" {
  family = "map-app" requires_compatibilities = ["FARGATE"] network_mode = "awsvpc"
  cpu = "512" memory = "1024" execution_role_arn = aws_iam_role.exec.arn
  container_definitions = jsonencode([{
    name = "app" image = var.image essential = true
    portMappings = [{ containerPort = 8000 }]
    environment = [{ name = "MAP_TRACES", value = "traces/spans.jsonl" }]
    logConfiguration = { logDriver = "awslogs" options = { awslogs-group = "/ecs/map" awslogs-region = var.region awslogs-stream-prefix = "app" } }
  }])
}
resource "aws_iam_role" "exec" {
  name = "map-ecs-exec"
  assume_role_policy = jsonencode({ Version = "2012-10-17" Statement = [{ Action = "sts:AssumeRole" Effect = "Allow" Principal = { Service = "ecs-tasks.amazonaws.com" } }] })
}
resource "aws_iam_role_policy_attachment" "exec" {
  role = aws_iam_role.exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_ecs_service" "app" {
  name = "map-app" cluster = aws_ecs_cluster.main.id task_definition = aws_ecs_task_definition.app.arn
  desired_count = 1 launch_type = "FARGATE"
  network_configuration { subnets = [aws_subnet.a.id] security_groups = [aws_security_group.app.id] assign_public_ip = true }
}
output "cluster" { value = aws_ecs_cluster.main.name }
# RDS Postgres (pgvector) and OpenSearch domain are intentionally left as
# managed services to attach via DATABASE_URL / OPENSEARCH_URL variables.
