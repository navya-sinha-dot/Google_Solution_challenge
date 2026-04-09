#!/usr/bin/env python3
"""
MQTT Broker Monitor
Subscribes to farm/sensors/# and displays all incoming messages in real-time
Works in VS Code Terminal without needing mosquitto_sub command

Usage:
    python mqtt_monitor.py 10.94.224.61 farm/sensors/#
    python mqtt_monitor.py <broker_ip> <topic>
"""

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import sys
from datetime import datetime

# Default values
BROKER_HOST = "192.168.137.83"
BROKER_PORT = 1883
TOPIC = "farm/sensors/#"

class MQTTMonitor:
    def __init__(self, broker_host, broker_port, topic):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.client = mqtt.Client(CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_connect_fail = self.on_connect_fail
        self.message_count = 0

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"\n[OK] Connected to broker: {self.broker_host}:{self.broker_port}")
            print(f"[*] Subscribing to: {self.topic}")
            print(f"[*] Waiting for messages...\n")
            print("=" * 80)
            print(f"{'Timestamp':<25} {'Topic':<35} {'Value':<20}")
            print("=" * 80)
            client.subscribe(self.topic)
        else:
            print(f"[ERROR] Connection failed with code {rc}")
            print(f"   Error codes:")
            print(f"   0 = Connection successful")
            print(f"   1 = Connection refused - incorrect protocol version")
            print(f"   2 = Connection refused - invalid client identifier")
            print(f"   3 = Connection refused - server unavailable")
            print(f"   4 = Connection refused - bad username or password")
            print(f"   5 = Connection refused - not authorised")

    def on_message(self, client, userdata, msg):
        self.message_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        topic = msg.topic
        payload = msg.payload.decode('utf-8') if isinstance(msg.payload, bytes) else str(msg.payload)
        
        # Format output
        print(f"{timestamp:<25} {topic:<35} {payload:<20}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"\n[ERROR] Unexpected disconnection (code {rc})")
        else:
            print(f"\n[OK] Disconnected gracefully")

    def on_connect_fail(self, client, userdata):
        print(f"\n[ERROR] Failed to connect to {self.broker_host}:{self.broker_port}")
        print(f"   Check if:")
        print(f"   - Broker is running")
        print(f"   - IP address is correct: {self.broker_host}")
        print(f"   - Port is correct: {self.broker_port}")
        print(f"   - Network connectivity is available")

    def start(self):
        try:
            print(f"\n[*] MQTT Broker Monitor")
            print(f"=" * 80)
            print(f"Broker: {self.broker_host}:{self.broker_port}")
            print(f"Topic:  {self.topic}")
            print(f"=" * 80)
            
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_forever()
        except Exception as e:
            print(f"\n[ERROR] {type(e).__name__}: {e}")
            print(f"\nTroubleshooting:")
            print(f"  - Verify broker IP: {self.broker_host}")
            print(f"  - Verify broker port: {self.broker_port}")
            print(f"  - Check network: ping {self.broker_host}")
            print(f"  - Check if Mosquitto is running on the broker")

def main():
    broker_host = sys.argv[1] if len(sys.argv) > 1 else BROKER_HOST
    topic = sys.argv[2] if len(sys.argv) > 2 else TOPIC
    
    monitor = MQTTMonitor(broker_host, BROKER_PORT, topic)
    monitor.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n[STOP] Monitor stopped by user")
        sys.exit(0)
