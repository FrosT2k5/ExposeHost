from exposehost.client import Client
import socket
import sys
from time import sleep 

proto = 'http'
if len(sys.argv) > 1 and sys.argv[1] == 'tcp':
    proto = 'tcp'

port = input("Port to forward: ")
subdomain = input("Subdomain: ")

client = Client('127.0.0.1', port, "exposehost.me", 1435, proto, subdomain)
# client = Client('127.0.0.1', port, "127.0.0.1", 1435, proto, subdomain)

# client.start()

# Start server without blocking
task = client.start_non_blocking()
print("Started non blocking")

# Check server connection status
print(client.get_status())
sleep(2)

# Check status after 2s (enough for successful connection), print URL
print(client.get_status())
print(client.get_url())

# The blocking call
task.result()
