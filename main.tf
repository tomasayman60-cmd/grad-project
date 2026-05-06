provider "aws" {
  region = "us-east-1"
}

# ============================================
# VPC
# ============================================

resource "aws_vpc" "main" {
  cidr_block = "172.16.0.0/16"

  tags = {
    Name = "main-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "172.16.2.0/24"
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "main-igw"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "public-rt"
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}

# ============================================
# Security Group
# ============================================

resource "aws_security_group" "ecourses_sg" {
  name        = "ecourses-sg"
  description = "Allow HTTP & SSH"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ecourses-sg"
  }
}

# ============================================
# AMI
# ============================================

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# ============================================
# EC2
# ============================================

resource "aws_instance" "ecourses_website" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public.id
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.ecourses_sg.id]

  user_data = <<-EOF
#!/bin/bash
yum update -y
yum install -y docker git python3-pip
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install docker-compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Python dependencies
pip3 install prometheus-client psutil boto3 requests

# Clone repository
cd /home/ec2-user
git clone https://github.com/tomasayman60-cmd/grad-project.git
cd grad-project

# Change INSTANCE_ID in monitoring_server.py
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
sed -i "s/i-xxxxxxxxxxxx/$INSTANCE_ID/" monitoring_server.py

# Run monitoring server in background
nohup python3 monitoring_server.py > /tmp/monitoring.log 2>&1 &

# Start Docker Compose
docker-compose up -d
EOF

  lifecycle {
    ignore_changes = [user_data]
  }

  tags = {
    Name = "ecourses-website"
  }
}

# ============================================
# UPDATE WITHOUT RECREATE
# ============================================

resource "null_resource" "deploy_update" {
  triggers = {
    always_run = timestamp()
  }

  connection {
    type        = "ssh"
    user        = "ec2-user"
    private_key = file("${var.key_name}.pem")
    host        = aws_instance.ecourses_website.public_ip
  }

  provisioner "remote-exec" {
    inline = [
      "cd /home/ec2-user/grad-project || git clone https://github.com/tomasayman60-cmd/grad-project.git",
      "cd /home/ec2-user/grad-project",
      "docker-compose down || true",
      "pkill -f monitoring_server.py || true",
      "git pull",
      "pip3 install -r requirements.txt || true",
      "nohup python3 monitoring_server.py > /tmp/monitoring.log 2>&1 &",
      "docker-compose up -d"
    ]
  }

  depends_on = [aws_instance.ecourses_website]
}

# ============================================
# OUTPUTS
# ============================================

output "instance_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_instance.ecourses_website.public_ip
}

output "website_url" {
  description = "Website URL"
  value       = "http://${aws_instance.ecourses_website.public_ip}"
}

output "prometheus_url" {
  description = "Prometheus UI URL"
  value       = "http://${aws_instance.ecourses_website.public_ip}:9090"
}

output "grafana_url" {
  description = "Grafana UI URL"
  value       = "http://${aws_instance.ecourses_website.public_ip}:3000"
}

output "metrics_url" {
  description = "Metrics endpoint"
  value       = "http://${aws_instance.ecourses_website.public_ip}:5000/metrics"
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh -i ${var.key_name}.pem ec2-user@${aws_instance.ecourses_website.public_ip}"
}

# ============================================
# VARIABLES
# ============================================

variable "key_name" {
  description = "EC2 Key Pair Name"
  type        = string
}