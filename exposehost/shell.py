from exposehost.client import Client
import asyncio
import sys
import logging
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

logger = logging.getLogger(__name__)

async def interactive_shell(client: Client):
    """
    Interactive shell for managing the tunnel and auth users at runtime.
    Logs are handled gracefully via patch_stdout.
    """
    # Create prompt session
    session = PromptSession()
    
    print("\n" + "="*50)
    print("ExposeHost Interactive Shell")
    print("Commands: add <user> <pass>, remove <user>, list, status, exit")
    print("="*50 + "\n")

    # Use patch_stdout context manager to handle log output
    with patch_stdout():
        while True:
            try:
                # This prompt will stay at the bottom while logs stream above
                text = await session.prompt_async("exposehost> ")
            except (EOFError, KeyboardInterrupt):
                break

            if not text:
                continue

            parts = text.strip().split()
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd == "exit":
                logger.info("Exiting shell...")
                break
            
            elif cmd == "add":
                if len(args) == 2:
                    client.add_auth_user(args[0], args[1])
                else:
                    print("Usage: add <username> <password>")
            
            elif cmd == "remove":
                if len(args) == 1:
                    client.remove_auth_user(args[0])
                else:
                    print("Usage: remove <username>")
            
            elif cmd == "list":
                if client.auth_proxy:
                    users = list(client.auth_proxy.users.keys())
                    print(f"Authorized users: {', '.join(users) if users else 'None'}")
                else:
                    print("Auth proxy is not running.")
            
            elif cmd == "status":
                print(f"Status: {client.get_status()}")
                print(f"URL: {client.get_url()}")
                if client.get_port():
                    print(f"Forwarded Port: {client.get_port()}")
            
            elif cmd == "help":
                print("\nAvailable Commands:")
                print("  add <user> <pass>   - Add or update a user")
                print("  remove <user>       - Remove a user")
                print("  list                - List all authorized users")
                print("  status              - Show connection status")
                print("  help                - Show this help message")
                print("  exit                - Exit the shell\n")
            
            else:
                print(f"Unknown command: {cmd}")
    
    # Clean shutdown of client if exit is called
    # We don't want to kill the client here if we just exit shell, 
    # but based on usage 'exit' usually means stop app.
    # However, since this runs in background loop, raising SystemExit is tricky.
    # We'll just return and let the caller decide what to do.
    return
