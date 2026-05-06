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