#!/bin/bash
yum update -y
yum install -y docker git
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Clone project files from GitHub (or copy from S3)
cd /home/ec2-user
git clone https://github.com/thomasaawaddockerest/ecourses-monitoring.git
cd ecourses-monitoring

# Run docker-compose to start all services
docker-compose up -d
