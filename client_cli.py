from exposehost.client import Client

port = input("Port to forward: ")
subdomain = input("Subdomain: ")
client = Client('127.0.0.1', port, '127.0.0.1', 1435, 'http', subdomain)
client.start()