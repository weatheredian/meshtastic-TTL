#THIS IS THE SCRIPT FOR THE RECEIVING DEVICE, like a base station
#the base station will receive countdown messages from the embedded device, and reply with okay messages.

import time
import sys
import threading
from pubsub import pub
from meshtastic.serial_interface import SerialInterface
from meshtastic import portnums_pb2

serial_port = '/dev/ttyUSB0'  # Replace with your Meshtastic device's serial port
destination_node_id = "!43b67cec"  # Replace with your target node's ID, the embedded device (TX)
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
            # Reply 'okay' to any message received from the destination node
            if fromnum == destination_node_id:
                interface.sendText("okay", destination_node_id)
                print(f"Replied 'okay' to {destination_node_id}")
    except KeyError:
        pass  # Ignore KeyError silently
    except UnicodeDecodeError:
        pass  # Ignore UnicodeDecodeError silently

def main():
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

    # Send intro message
    intro_message = "hello from HomeBeacon"
    local.sendText(intro_message, destination_node_id)
    print(f"Sent intro message to {destination_node_id}")

    # Only listen and reply once
    try:
        while not okay_event.is_set():
            sys.stdout.flush()
            time.sleep(1)
        # After replying once, keep listening (or exit if you want)
        print("Okay reply sent, RX script will now idle.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Script terminated by user")
        local.close()

if __name__ == "__main__":
    main()
