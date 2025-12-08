from exposehost.server import Server, MultiProcessingServer

server = MultiProcessingServer('127.0.0.1', 1435)
server.start()