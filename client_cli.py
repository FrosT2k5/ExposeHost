from exposehost.client import Client
import socket

# server_host = "exposehost.southindia.cloudapp.azure.com"
# server_ip = socket.gethostbyname(server_host)

port = input("Port to forward: ")
subdomain = input("Subdomain: ")
client = Client('127.0.0.1', port, "expose.exposehost.me", 1435, 'http', subdomain)
client.start()