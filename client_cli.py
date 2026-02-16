from exposehost.client import Client
import asyncio
import sys
import getpass
from time import sleep 
from exposehost.shell import interactive_shell

proto = 'http'  # Default to HTTP
auth_enabled = False
auth_users = {}

if len(sys.argv) > 1:
    if sys.argv[1] == 'tcp':
        proto = 'tcp'
    elif sys.argv[1] == 'auth':
        # Auth mode - stays HTTP but enables authentication
        auth_enabled = True
        user = input("Auth Username: ")
        password = getpass.getpass("Auth Password: ")
        auth_users[user] = password

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
    auth_users=auth_users
)

# Start server without blocking (returns a Future for connection task)
task = client.start_non_blocking()
print("Tunnel starting...")

# Check server connection status
print(f"Status: {client.get_status()}")
sleep(2)

# Check status after 2s (enough for successful connection), print URL
print(f"Status: {client.get_status()}")
print(f"URL: {client.get_url()}")

if auth_enabled:
    # Submit the interactive shell coroutine to the client's running loop
    shell_future = asyncio.run_coroutine_threadsafe(
        interactive_shell(client), 
        client.loop
    )
    
    # Block main thread until shell exits (user types 'exit')
    try:
        shell_future.result()
    except KeyboardInterrupt:
        pass
else:
    # Standard blocking mode
    # Wait for the background connection task
    try:
        task.result()
    except KeyboardInterrupt:
        pass
