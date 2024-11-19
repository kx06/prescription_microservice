from kafka import KafkaConsumer
from kafka import KafkaProducer
import json

consumer = KafkaConsumer(
    'critical_logs',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# producer = KafkaProducer(value_serializer=lambda m: json.dumps(m).encode("utf-8"))
# producer.send(None)



for message in consumer:
    message_value = message.value
    print(message_value)
