from exposehost.client import Client

client = Client('127.0.0.1', 4444, '127.0.0.1', 1435, 'tcp')
client.start()