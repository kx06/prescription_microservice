from kafka import KafkaConsumer, KafkaProducer
import json
from datetime import datetime, timedelta
import threading

consumer = KafkaConsumer(
    'logs',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

HEARTBEAT_TIMEOUT = timedelta(seconds=120)
HEARTBEAT_CHECK_INTERVAL = 90

heartbeat_tracker = {}  
services = {}
node_timers = {}

def check_heartbeat_timeout(node_id):
    if node_id in heartbeat_tracker and node_id in services:
        current_time = datetime.now()
        last_heartbeat = heartbeat_tracker[node_id]
        time_diff = current_time - last_heartbeat

        if time_diff.total_seconds() > HEARTBEAT_CHECK_INTERVAL:
            alert_message = {
                'node_id': node_id,
                'message_type': 'ALERT',
                'status': 'NODE FAILURE',
                'alert_generated_at': current_time.isoformat()
            }
            producer.send('node_failure', alert_message)
            producer.send('all_logs', alert_message)
            print(f"Sent to node_failure and all_logs: {alert_message}")

            registry_message = {
                "message_type": "REGISTRATION",
                "node_id": node_id,
                "service_name": services[node_id],
                "status": "DOWN",
                "timestamp": current_time.isoformat()
            }
            producer.send('critical_logs', registry_message)
            producer.send('all_logs', registry_message)
            print(f"Updated registry to DOWN and sent to critical_logs and all_logs: {registry_message}")

            del heartbeat_tracker[node_id]
            del services[node_id]
            if node_id in node_timers:
                del node_timers[node_id]

def schedule_heartbeat_check(node_id):
    timer = threading.Timer(HEARTBEAT_CHECK_INTERVAL, check_heartbeat_timeout, args=[node_id])
    timer.daemon = True
    timer.start()
    node_timers[node_id] = timer

    
for message in consumer:
    message_value = message.value
    
    producer.send('all_logs', message_value)
    print(f"Forwarded message to all_logs: {message_value}")
    
    mval = json.loads(message_value['message'].replace("'", '"'))
    node_id = mval['node_id']
    message_type = mval['message_type']
    timestamp = datetime.strptime(mval['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
    current_time = datetime.now()

    if message_type == 'HEARTBEAT':
        status = mval.get('status', 'UP')
        
        if status == 'DOWN':
            if node_id in services:
                registry_message = {
                    "message_type": "REGISTRATION",
                    "node_id": node_id,
                    "service_name": services[node_id],
                    "status": "DOWN",
                    "timestamp": current_time.isoformat()
                }
                producer.send('critical_logs', registry_message)
                producer.send('all_logs', registry_message)
                print(f"Service down, sent to critical_logs and all_logs: {registry_message}")

                if node_id in node_timers:
                    node_timers[node_id].cancel()
                    del node_timers[node_id]
                if node_id in heartbeat_tracker:
                    del heartbeat_tracker[node_id]
                del services[node_id]
        else:
            heartbeat_tracker[node_id] = timestamp
            if node_id in node_timers:
                node_timers[node_id].cancel()
            schedule_heartbeat_check(node_id)

    elif message_type == 'REGISTRATION':
        service_name = mval.get('service_name', 'unknown')
        services[node_id] = service_name
        
        registry_message = {
            "message_type": "REGISTRATION",
            "node_id": node_id,
            "service_name": service_name,
            "status": "UP",
            "timestamp": current_time.isoformat()
        }
        producer.send('critical_logs', registry_message)
        producer.send('all_logs', registry_message)
        print(f"Sent to critical_logs and all_logs: {registry_message}")
    
    elif message_type == 'LOG' and mval['log_level'] == 'ERROR':
        producer.send('critical_logs', message_value)
