import asyncio
import logging
import sys
import json
import base64
import hmac
import hashlib
import time
from aiohttp import web, ClientSession
from exposehost.helpers import random_string

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Auth cookie configuration
AUTH_COOKIE_NAME = 'exposehost_auth_session'

# Streaming configuration
CHUNK_SIZE = 4096  # Bytes to stream per chunk


# Embedded login page HTML with CSS
LOGIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authentication Required - ExposeHost</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0a0a0c;
            --bg-2: #111114;
            --border: #252529;
            --text: #f4f4f5;
            --text-2: #a1a1aa;
            --primary: #6366f1;
            --accent: #22d3ee;
            --font: 'Inter', system-ui, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font);
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-card {
            background: var(--bg-2);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.2);
        }
        .logo {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 30px;
            font-size: 20px;
            font-weight: 600;
        }
        .accent { color: var(--accent); }
        h1 {
            font-size: 24px;
            margin-bottom: 8px;
            text-align: center;
            font-weight: 600;
        }
        .subtitle {
            color: var(--text-2);
            text-align: center;
            margin-bottom: 32px;
            font-size: 14px;
        }
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            font-weight: 500;
            color: var(--text-2);
        }
        input {
            width: 100%;
            padding: 12px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-family: inherit;
            font-size: 14px;
            transition: border-color 0.15s;
        }
        input:focus {
            outline: none;
            border-color: var(--primary);
        }
        button {
            width: 100%;
            padding: 12px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: opacity 0.15s;
        }
        button:hover { opacity: 0.9; }
        .error {
            background: rgba(255, 95, 87, 0.1);
            color: #ff5f57;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 24px;
            font-size: 14px;
            text-align: center;
            border: 1px solid rgba(255, 95, 87, 0.2);
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo">
            <svg width="32" height="32" viewBox="0 0 40 40" fill="none">
                <path d="M4 20C4 12 10 6 20 6C30 6 36 12 36 20" stroke="url(#logoGrad)" stroke-width="3" stroke-linecap="round"/>
                <path d="M20 34L20 18" stroke="url(#logoGrad)" stroke-width="3" stroke-linecap="round"/>
                <path d="M14 24L20 18L26 24" stroke="url(#logoGrad)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="20" cy="34" r="3" fill="url(#logoGrad)"/>
                <defs>
                    <linearGradient id="logoGrad" x1="20" y1="34" x2="20" y2="6">
                        <stop offset="0%" stop-color="#6366f1"/>
                        <stop offset="100%" stop-color="#22d3ee"/>
                    </linearGradient>
                </defs>
            </svg>
            <span>Expose<span class="accent">Host</span></span>
        </div>
        <h1>Accessing this page requires authorization</h1>
        <p class="subtitle">Please sign in to continue</p>
        <!-- ERROR_HTML -->
        <form method="POST" action="/auth-login">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autofocus autocomplete="username">
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required autocomplete="current-password">
            </div>
            <button type="submit">Sign In</button>
        </form>
    </div>
</body>
</html>"""


class AuthProxyServer:
    """
    HTTP authentication proxy server that sits between the tunnel and the actual service.
    Handles login, session management, and streaming proxy to the actual service.
    """
    
    
    def __init__(self, users: dict[str, str], actual_service_port: int):
        # Users is a list of dicts: [{'username': 'u', 'password': 'p'}, ...]
        self.users = users
        self.actual_port = actual_service_port
        self.secret_key = random_string(32)  # For signing session tokens
        self.app = None
        self.runner = None
        self.site = None
        self.proxy_port = None
        
    async def start(self) -> int:
        """Start the auth proxy server and return the port number"""
        self.app = web.Application()
        self.app.router.add_route('*', '/auth-login', self.handle_login)
        self.app.router.add_route('*', '/{path:.*}', self.handle_request)
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        # Bind to random available port
        self.site = web.TCPSite(self.runner, 'localhost', 0)
        await self.site.start()
        
        # Get the actual port assigned
        self.proxy_port = self.site._server.sockets[0].getsockname()[1]
        logger.info("Auth proxy server started on localhost:%s", self.proxy_port)
        return self.proxy_port
    
    async def stop(self):
        """Cleanup and shutdown the auth proxy server"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Auth proxy server stopped")
            
    def add_user(self, username, password):
        """Add or update a user"""
        self.users[username] = password
        logger.info("Added/Updated user: %s", username)
        
    def remove_user(self, username):
        """Remove a user"""
        if username in self.users:
            del self.users[username]
            logger.info("Removed user: %s", username)
    
    def create_session_token(self, username) -> str:
        """Create a signed session token"""
        payload = {
            'username': username,
            'expires': time.time() + 3600,  # 1 hour expiration
            'nonce': random_string(16)
        }
        token_data = base64.b64encode(json.dumps(payload).encode()).decode()
        signature = hmac.new(
            self.secret_key.encode(),
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{token_data}.{signature}"
    
    def verify_session(self, token: str) -> bool:
        """Verify session token signature and expiration"""
        if not token:
            return False
        
        try:
            parts = token.rsplit('.', 1)
            if len(parts) != 2:
                return False
            
            token_data, signature = parts
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key.encode(),
                token_data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if signature != expected_signature:
                logger.debug("Invalid token signature")
                return False
            
            # Verify expiration
            payload = json.loads(base64.b64decode(token_data))
            if payload['expires'] < time.time():
                logger.debug("Session token expired")
                return False
            
            # Check if user still exists
            username = payload.get('username')
            if username not in self.users:
                logger.debug("User %s no longer exists", username)
                return False

            # Log successful verification
            logger.debug("Session verified for user: %s", username)
            return True
        except Exception as e:
            logger.error("Error verifying session token: %s", e)
            return False
    
    def render_login_page(self, error: str = None) -> web.Response:
        """Render the login page with optional error message"""
        error_html = f'<div class="error">{error}</div>' if error else ''
        html = LOGIN_PAGE_HTML.replace('<!-- ERROR_HTML -->', error_html)
        return web.Response(text=html, content_type='text/html')
    
    async def handle_login(self, request: web.Request) -> web.Response:
        """Handle login POST request"""
        if request.method != 'POST':
            return self.render_login_page()
        
        try:
            data = await request.post()
            username = data.get('username', '')
            password = data.get('password', '')
            
            if username in self.users and self.users[username] == password:
                # Successful login - set session cookie and redirect
                logger.info("Successful authentication for user: %s", username)
                response = web.Response(status=302)
                response.headers['Location'] = '/'
                
                # Create session token with username
                token = self.create_session_token(username)
                
                response.set_cookie(
                    AUTH_COOKIE_NAME,
                    token,
                    httponly=True,
                    secure=True,
                    max_age=3600,
                    samesite='Lax'
                )
                return response
            else:
                # Invalid credentials
                logger.warning("Failed authentication attempt for user: %s", username)
                return self.render_login_page(error="Invalid username or password")
        
        except Exception as e:
            logger.error("Error handling login: %s", e)
            return self.render_login_page(error="An error occurred during login")
    
    async def handle_request(self, request: web.Request) -> web.Response:
        """Main request handler - check session and proxy to service"""
        # Check for valid session cookie
        session_cookie = request.cookies.get(AUTH_COOKIE_NAME)
        
        if self.verify_session(session_cookie):
            # Valid session - proxy to actual service
            return await self.proxy_to_service(request)
        else:
            # No valid session - show login page
            return self.render_login_page()
    
    async def proxy_to_service(self, request: web.Request) -> web.StreamResponse:
        """Stream proxy request to actual service"""
        try:
            # Build target URL
            url = f'http://localhost:{self.actual_port}{request.path_qs}'
            
            # Prepare headers (remove hop-by-hop headers and Cookie header)
            headers = dict(request.headers)
            headers.pop('Host', None)
            headers.pop('Cookie', None)  # We'll pass cookies separately
            
            # Filter out only auth cookie, keep all other cookies
            service_cookies = {k: v for k, v in request.cookies.items() 
                             if k != AUTH_COOKIE_NAME}
            
            async with ClientSession() as session:
                # Make request to actual service
                # aiohttp will automatically build the Cookie header from cookies dict
                async with session.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    cookies=service_cookies,  # Built-in cookie handling
                    data=request.content,  # Streams automatically
                    allow_redirects=False
                ) as resp:
                    # Create streaming response
                    response = web.StreamResponse(
                        status=resp.status,
                        reason=resp.reason,
                        headers=resp.headers
                    )
                    
                    await response.prepare(request)
                    
                    # Stream response body in chunks
                    async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                        await response.write(chunk)
                    
                    await response.write_eof()
                    return response
        
        except Exception as e:
            logger.error("Error proxying to service: %s", e)
            return web.Response(
                text="502 Bad Gateway - Could not connect to service",
                status=502,
                content_type='text/plain'
            )
