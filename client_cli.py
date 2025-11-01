from exposehost.client import Client
import socket
import sys

proto = 'http'
if len(sys.argv) > 1 and sys.argv[1] == 'tcp':
    proto = 'tcp'

port = input("Port to forward: ")
subdomain = input("Subdomain: ")

client = Client('127.0.0.1', port, "exposehost.me", 1435, proto, subdomain)
client.start()
