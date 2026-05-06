import requests
import boto3
import time
import logging
import smtplib
import random
import psutil
from email.mime.text import MIMEText
from datetime import datetime
from prometheus_client import Gauge, start_http_server

# ================= PROMETHEUS METRICS =================
temperature_gauge = Gauge('temperature_celsius', 'Current temperature in Celsius')
active_users_gauge = Gauge('active_users', 'Number of currently active users')
cpu_usage_gauge = Gauge('cpu_usage_percent', 'CPU usage percentage')

# ================= CONFIG =================
INSTANCE_ID = "i-xxxxxxxxxxxx"  # CHANGE THIS!
REGION = "us-east-1"
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"
CHECK_INTERVAL = 60
SCALE_UP_THRESHOLD = 80
SCALE_DOWN_THRESHOLD = 10
IDLE_THRESHOLD = 0
IDLE_TIME = 300

INSTANCE_TYPES = {
    "low": "t3.micro",
    "high": "t3.large"
}

EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender": "tomascloudacc@gmail.com",
    "password": "oovw hupn zvyb dujm",
    "receiver": "tomascloudacc@gmail.com"
}

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

ec2 = boto3.client("ec2", region_name=REGION)
last_low_traffic_notification = 0
last_idle_notification = 0

# ================= METRICS UPDATER =================
def update_metrics():
    """Update Prometheus gauges with random/demo values"""
    temperature_gauge.set(22.5 + random.uniform(-2, 2))
    active_users_gauge.set(random.randint(10, 100))
    cpu_usage_gauge.set(psutil.cpu_percent())

# ================= SCALING FUNCTIONS =================
def get_metric(metric_name):
    try:
        response = requests.get(PROMETHEUS_URL, params={"query": metric_name})
        data = response.json()
        if data["data"]["result"]:
            return float(data["data"]["result"][0]["value"][1])
        return 0
    except Exception as e:
        logging.error(f"Error fetching metric: {e}")
        return 0

def get_instance_type():
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    return response['Reservations'][0]['Instances'][0]['InstanceType']

def stop_instance():
    logging.info("Stopping instance...")
    ec2.stop_instances(InstanceIds=[INSTANCE_ID])
    send_email("⚠️ EC2 Stopped - No Traffic", f"Instance {INSTANCE_ID} stopped.")

def change_instance_type(new_type):
    current_type = get_instance_type()
    if current_type == new_type:
        logging.info(f"Already running on {new_type}")
        return
    logging.info(f"Changing instance from {current_type} to {new_type}")
    ec2.stop_instances(InstanceIds=[INSTANCE_ID])
    waiter = ec2.get_waiter('instance_stopped')
    waiter.wait(InstanceIds=[INSTANCE_ID])
    ec2.modify_instance_attribute(InstanceId=INSTANCE_ID, Attribute='instanceType', Value=new_type)
    ec2.start_instances(InstanceIds=[INSTANCE_ID])
    send_email("🔄 EC2 Scaled Successfully", f"Instance type changed from {current_type} to {new_type}")

def send_email(subject, body):
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG["sender"]
        msg['To'] = EMAIL_CONFIG["receiver"]
        server = smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.starttls()
        server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        server.send_message(msg)
        server.quit()
        logging.info(f"✅ Email sent: {subject}")
        return True
    except Exception as e:
        logging.error(f"❌ Email error: {e}")
        return False

def send_low_traffic_notification(users, cpu):
    subject = "📉 Low Traffic Alert"
    body = f"Instance {INSTANCE_ID} has low traffic: {users} users, {cpu}% CPU."
    return send_email(subject, body)

def send_idle_warning_notification(remaining_time):
    subject = "⚠️ Instance Idle Warning"
    body = f"Instance {INSTANCE_ID} idle. Stopping in {remaining_time:.0f} seconds."
    return send_email(subject, body)

def is_instance_running():
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    state = response['Reservations'][0]['Instances'][0]['State']['Name']
    return state == "running"

def start_instance_if_needed():
    if not is_instance_running():
        logging.info("Starting instance...")
        ec2.start_instances(InstanceIds=[INSTANCE_ID])
        send_email("▶️ EC2 Started", f"Instance {INSTANCE_ID} started.")

# ================= MAIN LOOP =================
def main():
    global last_low_traffic_notification
    idle_start_time = None
    warning_sent = False

    # Start Prometheus metrics server
    start_http_server(5000)
    logging.info("✅ Metrics server running on port 5000")

    while True:
        # Update metrics every 5 seconds
        update_metrics()

        # Get current values
        users = random.randint(10, 100)  # For demo - replace with actual metric fetch
        cpu = psutil.cpu_percent()

        logging.info(f"📊 Users: {users} | CPU: {cpu}%")

        # Scale up/down logic
        if users > SCALE_UP_THRESHOLD:
            start_instance_if_needed()
            change_instance_type(INSTANCE_TYPES["high"])
        elif 0 < users <= SCALE_DOWN_THRESHOLD:
            current_time = time.time()
            if current_time - last_low_traffic_notification > 300:
                send_low_traffic_notification(users, cpu)
                last_low_traffic_notification = current_time

        # Idle detection
        if users == IDLE_THRESHOLD:
            if idle_start_time is None:
                idle_start_time = time.time()
                warning_sent = False
            else:
                elapsed = time.time() - idle_start_time
                remaining = IDLE_TIME - elapsed
                if remaining <= 30 and remaining > 0 and not warning_sent:
                    send_idle_warning_notification(remaining)
                    warning_sent = True
                if elapsed > IDLE_TIME:
                    stop_instance()
                    idle_start_time = None
                    warning_sent = False
        else:
            idle_start_time = None
            warning_sent = False

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    logging.info("🚀 Starting Cloud Optimizer with Prometheus Metrics...")
    main()