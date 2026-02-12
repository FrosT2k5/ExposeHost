from exposehost.client import Client
import socket
import sys
import getpass
from time import sleep 

proto = 'http'  # Default to HTTP
auth_enabled = False
auth_user = None
auth_pass = None

if len(sys.argv) > 1:
    if sys.argv[1] == 'tcp':
        proto = 'tcp'
    elif sys.argv[1] == 'auth':
        # Auth mode - stays HTTP but enables authentication
        auth_enabled = True
        auth_user = input("Auth Username: ")
        auth_pass = getpass.getpass("Auth Password: ")

port = input("Port to forward: ")
subdomain = input("Subdomain: ")

client = Client(
    '127.0.0.1', 
    int(port), 
    "exposehost.me", 
    1435, 
    proto, 
    subdomain,
    auth_enabled=auth_enabled,
    auth_user=auth_user,
    auth_pass=auth_pass
)
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
