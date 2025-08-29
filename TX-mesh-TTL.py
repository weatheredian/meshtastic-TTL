#THIS IS THE SCRIPT FOR THE EMBEDDED DEVICE
#the embedded device will send countdown messages to the base station
import RPi.GPIO as GPIO
import time
import sys
import threading
from pubsub import pub
from meshtastic.serial_interface import SerialInterface
from meshtastic import portnums_pb2

serial_port = '/dev/ttyUSB0'  # Replace with your Meshtastic device's serial port
destination_node_id = "!bdf0a688"  # Replace with your target node's ID, the base station (RX)
time_to_live = 18000  # TTL value in seconds
message_interval = 10  # interval between messages in seconds

okay_event = threading.Event()

def get_node_info(serial_port):
    print("Initializing SerialInterface to get node info...")
    local = SerialInterface(serial_port)
    node_info = local.nodes
    local.close()
    print("Node info retrieved.")
    return node_info

def parse_node_info(node_info):
    print("Parsing node info...")
    nodes = []
    for node_id, node in node_info.items():
        nodes.append({
            'num': node_id,
            'user': {
                'shortName': node.get('user', {}).get('shortName', 'Unknown')
            }
        })
    print("Node info parsed.")
    return nodes

def on_receive(packet, interface, node_list):
    try:
        if packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            message = packet['decoded']['payload'].decode('utf-8')
            fromnum = packet['fromId']
            shortname = next((node['user']['shortName'] for node in node_list if node['num'] == fromnum), 'Unknown')
            print(f"{shortname}: {message}")
            # Signal event if 'okay' is found in message from destination node
            if fromnum == destination_node_id and 'okay' in message.lower():
                okay_event.set()
    except KeyError:
        pass  # Ignore KeyError silently
    except UnicodeDecodeError:
        pass  # Ignore UnicodeDecodeError silently

def main():
    grace_points = 5
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    NODE_LOST_PIN = 18  # Use GPIO 17, change if needed
    GPIO.setup(NODE_LOST_PIN, GPIO.OUT)
    GPIO.output(NODE_LOST_PIN, GPIO.LOW)
    print(f"Using serial port: {serial_port}")

    # Retrieve and parse node information
    node_info = get_node_info(serial_port)
    node_list = parse_node_info(node_info)

    # Print node list for debugging
    print("Node List:")
    for node in node_list:
        print(node)

    # Subscribe the callback function to message reception
    def on_receive_wrapper(packet, interface):
        on_receive(packet, interface, node_list)

    pub.subscribe(on_receive_wrapper, "meshtastic.receive")
    print("Subscribed to meshtastic.receive")

    # Set up the SerialInterface for message listening and sending
    local = SerialInterface(serial_port)
    print("SerialInterface setup for listening and sending.")

    # Set node GPS coordinates
    latitude = 37.2431
    longitude = -115.7930
    altitude = 0  # Set altitude to 0 or your desired value
    local.sendPosition(latitude, longitude, altitude)
    print(f"Set node GPS position to {latitude}, {longitude}")

    # Send intro message
    intro_message = "hello from WeatheredOne"
    local.sendText(intro_message, destination_node_id)
    print(f"Sent intro message to {destination_node_id}")

    # TTL message loop
    ttl = time_to_live
    try:
        for i in range(int(time_to_live / message_interval)):
            ttl_message = f"remaining time: {ttl} seconds"
            okay_event.clear()
            local.sendText(ttl_message, destination_node_id)
            print(f"Sent message to {destination_node_id}: {ttl_message}")

            # Wait for 'okay' message for up to message_interval seconds
            waited = okay_event.wait(timeout=message_interval)
            if not waited:
                # Start 60 second countdown for 'okay' message
                print("No 'okay' received, starting 60 second countdown...")
                countdown = 60
                countdown_okay = False
                while countdown > 0:
                    if okay_event.wait(timeout=1):
                        print("'okay' received during countdown, resuming normal mode.")
                        countdown_okay = True
                        break
                    countdown -= 1
                if not countdown_okay:
                    # Countdown finished without 'okay'
                    print("countdown ended, retracting grace point")
                    local.sendText("reducing one grace point", destination_node_id)
                    grace_points = grace_points - 1
                    if grace_points == 0:
                        print("node lost, node lost, node lost")
                        GPIO.output(NODE_LOST_PIN, GPIO.HIGH)
                        local.sendText("node lost, terminating", destination_node_id)
                        local.close()
                        GPIO.cleanup()
                        sys.exit(0)
            ttl -= message_interval
            time.sleep(message_interval)

        # Keep the script running to listen for messages
        while True:
            sys.stdout.flush()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Script terminated by user")
        local.close()

if __name__ == "__main__":
    main()
