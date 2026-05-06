output "instance_public_ip" {
  description = "Public IP of the web server (public subnet)"
  value       = aws_instance.ecourses_website.public_ip
}

output "instance_public_dns" {
  description = "Public DNS of the web server"
  value       = aws_instance.ecourses_website.public_dns
}

output "website_url" {
  description = "URL to access the website"
  value       = "http://${aws_instance.ecourses_website.public_ip}"
}

output "ssh_command" {
  description = "SSH command to connect to the web server"
  value       = "ssh -i ${var.key_name}.pem ec2-user@${aws_instance.ecourses_website.public_ip}"
}

output "instance_id" {
  description = "Instance ID of the web server"
  value       = aws_instance.ecourses_website.id
}

output "private_instance_id" {
  description = "Instance ID of the private EC2 (no public IP)"
  value       = aws_instance.private_ec2.id
}

output "private_instance_private_ip" {
  description = "Private IP of the private EC2"
  value       = aws_instance.private_ec2.private_ip
}