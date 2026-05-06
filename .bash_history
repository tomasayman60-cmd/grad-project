#1777824113
ls
#1777824215
ssh -i "tf.pem" ec2-user@13.51.238.157
#1777824971
pip install prometheus-client psutil
#1777824982
python3 app.py
#1777825490
mkdir ~/monitoring
#1777825505
cd ~/monitoring
#1777825527
sudo docker-compose up -d
#1777825568
who
#1777825625
cd ~/monitoring  
#1777825641
sudo docker-compose up -d
#1777825700
scp -i tf.pem docker-compose.yml metrics.py prometheus.yml ec2-user@13.51.238.157:~/monitoring/
#1777826563
cat > metrics.py << 'EOF'
from prometheus_client import Gauge, start_http_server
import random
import time
import psutil
temperature_gauge = Gauge('temperature_celsius', 'Current temperature in Celsius')
active_users = Gauge('active_users', 'Number of currently active users')
cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')

start_http_server(5000)

print("Metrics server running on port 5000...")

while True:
    temperature_gauge.set(22.5 + random.uniform(-2, 2))
    active_users.set(random.randint(10, 100))
    cpu_usage.set(psutil.cpu_percent())
    time.sleep(5)
EOF

#1777826606
# اعمل ملف prometheus.yml
#1777826607
cat > prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'ecourses'
    static_configs:
      - targets: ['ecourses:5000']

  - job_name: 'metrics'
    static_configs:
      - targets: ['ecourses:5000']
    metrics_path: '/metrics'
EOF

#1777826609
# اعمل ملف docker-compose.yml
#1777826609
cat > docker-compose.yml << 'EOF'
version: "3.8"

services:
  ecourses:
    image: thomasaawaddockerest/ecourses_web-fe:latest
    ports:
      - "5000:5000"
      - "80:80"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    restart: unless-stopped
EOF

#1777826638
cd ~/monitoring
#1777826654
sudo docker-compose down
