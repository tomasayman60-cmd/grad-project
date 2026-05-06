import requests
import boto3
import time
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# ================= CONFIG =================
INSTANCE_ID = "i-xxxxxxxxxxxx"
REGION = "us-east-1"

PROMETHEUS_URL = "http://localhost:9090/api/v1/query"

CHECK_INTERVAL = 60        # seconds
SCALE_UP_THRESHOLD = 80    # active users
SCALE_DOWN_THRESHOLD = 10  # NEW: threshold for low traffic notification
IDLE_THRESHOLD = 0         # no users
IDLE_TIME = 300            # seconds before stopping

INSTANCE_TYPES = {
    "low": "t3.micro",
    "high": "t3.large"
}

# Email Configuration - UPDATE THESE VALUES
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",  # For Gmail
    "smtp_port": 587,
    "sender": "tomascloudacc@gmail.com",  # Your Gmail address
    "password": "oovw hupn zvyb dujm",   # Gmail App Password (NOT regular password)
    "receiver": "tomascloudacc@gmail.com"  # Where to send notifications
}

# ==========================================

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# AWS Client
ec2 = boto3.client("ec2", region_name=REGION)

# Track if we already sent low traffic notification
last_low_traffic_notification = 0
last_idle_notification = 0

# ==========================================

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

# ==========================================

def get_instance_type():
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    return response['Reservations'][0]['Instances'][0]['InstanceType']

# ==========================================

def stop_instance():
    logging.info("Stopping instance...")
    ec2.stop_instances(InstanceIds=[INSTANCE_ID])
    send_email(
        "⚠️ EC2 Stopped - No Traffic", 
        f"Instance {INSTANCE_ID} has been stopped due to prolonged inactivity.\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Reason: No active users for {IDLE_TIME} seconds."
    )

# ==========================================

def change_instance_type(new_type):
    current_type = get_instance_type()

    if current_type == new_type:
        logging.info(f"Already running on {new_type}")
        return

    logging.info(f"Changing instance from {current_type} to {new_type}")

    ec2.stop_instances(InstanceIds=[INSTANCE_ID])
    waiter = ec2.get_waiter('instance_stopped')
    waiter.wait(InstanceIds=[INSTANCE_ID])

    ec2.modify_instance_attribute(
        InstanceId=INSTANCE_ID,
        Attribute='instanceType',
        Value=new_type
    )

    ec2.start_instances(InstanceIds=[INSTANCE_ID])

    send_email(
        "🔄 EC2 Scaled Successfully",
        f"Instance type changed from {current_type} to {new_type}\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Instance ID: {INSTANCE_ID}\n"
        f"Region: {REGION}"
    )

# ==========================================

def send_email(subject, body):
    """Send email notification"""
    try:
        # Create message
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG["sender"]
        msg['To'] = EMAIL_CONFIG["receiver"]
        
        # Add timestamp in header
        msg['X-Timestamp'] = datetime.now().isoformat()

        # Connect and send
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

# ==========================================

def send_low_traffic_notification(users, cpu):
    """Send notification when traffic is low"""
    subject = "📉 Low Traffic Alert"
    body = f"""
    EC2 Instance Traffic Report:
    =============================
    Instance ID: {INSTANCE_ID}
    Region: {REGION}
    Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Current Metrics:
    - Active Users: {users}
    - CPU Usage: {cpu}%
    
    Threshold Values:
    - Scale Down Threshold: {SCALE_DOWN_THRESHOLD} users
    - Idle Threshold: {IDLE_THRESHOLD} users
    
    Action: Monitoring traffic. Will stop if no users for {IDLE_TIME} seconds.
    """
    
    return send_email(subject, body)

# ==========================================

def send_idle_warning_notification(remaining_time):
    """Send warning before stopping instance"""
    subject = "⚠️ Instance Idle Warning"
    body = f"""
    EC2 Instance Idle Warning
    =========================
    Instance ID: {INSTANCE_ID}
    Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    No active users detected!
    Instance will be stopped in {remaining_time:.0f} seconds.
    
    Action Required: Send traffic to the instance to prevent shutdown.
    """
    
    return send_email(subject, body)

# ==========================================

def is_instance_running():
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    state = response['Reservations'][0]['Instances'][0]['State']['Name']
    return state == "running"

# ==========================================

def start_instance_if_needed():
    if not is_instance_running():
        logging.info("Starting instance...")
        ec2.start_instances(InstanceIds=[INSTANCE_ID])
        send_email(
            "▶️ EC2 Started - Traffic Detected", 
            f"Instance {INSTANCE_ID} has been started in {REGION}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Reason: Incoming traffic detected."
        )

# ==========================================

def main():
    global last_low_traffic_notification, last_idle_notification
    idle_start_time = None
    warning_sent = False

    while True:
        users = get_metric("active_users")
        cpu = get_metric("cpu_usage_percent")

        logging.info(f"📊 Users: {users} | CPU: {cpu}%")

        # ===== LOW TRAFFIC NOTIFICATION =====
        if 0 < users <= SCALE_DOWN_THRESHOLD:
            current_time = time.time()
            # Send notification every 5 minutes for low traffic
            if current_time - last_low_traffic_notification > 300:  # 5 minutes
                send_low_traffic_notification(users, cpu)
                last_low_traffic_notification = current_time

        # ===== SCALE UP =====
        if users > SCALE_UP_THRESHOLD:
            start_instance_if_needed()
            change_instance_type(INSTANCE_TYPES["high"])
            idle_start_time = None
            warning_sent = False

        # ===== IDLE DETECTION =====
        elif users == IDLE_THRESHOLD:
            if idle_start_time is None:
                idle_start_time = time.time()
                warning_sent = False
                logging.info("⏰ Idle timer started...")
            
            else:
                elapsed = time.time() - idle_start_time
                remaining = IDLE_TIME - elapsed
                
                # Send warning when 30 seconds remaining
                if remaining <= 30 and remaining > 0 and not warning_sent:
                    send_idle_warning_notification(remaining)
                    warning_sent = True
                
                # Stop instance after idle time
                if elapsed > IDLE_TIME:
                    stop_instance()
                    # Reset after stop
                    idle_start_time = None
                    warning_sent = False
                    
        else:
            # Reset idle detection when users > 0
            if idle_start_time is not None:
                logging.info("🔄 Idle timer reset - traffic detected")
                idle_start_time = None
                warning_sent = False

        time.sleep(CHECK_INTERVAL)

# ==========================================

if __name__ == "__main__":
    logging.info("🚀 Starting Cloud Optimizer with Email Notifications...")
    logging.info(f"📧 Email notifications will be sent to: {EMAIL_CONFIG['receiver']}")
    main()