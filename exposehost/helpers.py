import os
from binascii import hexlify
import re
from pathlib import Path
import logging
import subprocess


HOME_DIR = Path.home()
NGINX_CONFIG_DIR = HOME_DIR / "nginx"


def random_string(length: int):
    r_string = hexlify(os.urandom(length)).decode()

    # r_string will be of twice the size of length 
    # since each byte contains 2 hex chars eg: 0xaa (1byte, but 2 chars)
    # return sliced string with length
    return r_string[0:length]


def clean_all_nginx_configs():
    for filename in os.listdir(NGINX_CONFIG_DIR):
        file_path = os.path.join(NGINX_CONFIG_DIR, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            logging.error('Failed to delete %s. Reason: %s' % (file_path, e))


def restart_nginx():
    subprocess.run("sudo /usr/bin/systemctl reload nginx", shell=True)


def generate_nginx_http_config(full_domain: str, port: int):
    # TODO: env variables, for the ssl cert here 
    default_config = """server {
    listen 443 ssl;
    server_name example.domain.com;

    ssl_certificate     /home/yash/Desktop/programming/python/ExposeHost/exposehost/keys/test_certificate.pem;
    ssl_certificate_key /home/yash/Desktop/programming/python/ExposeHost/exposehost/keys/test_private_key.pem;
    ssl_protocols TLSv1.2 TLSv1.1 TLSv1;

    location / {
        proxy_pass http://0.0.0.0:9999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name example.domain.com;

    location / {
        proxy_pass http://0.0.0.0:9999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
    """

    new_config = re.sub(r"example\.domain\.com", full_domain, default_config, 2, re.MULTILINE)
    new_config = re.sub(r"9999", str(port), new_config, 2, re.MULTILINE)

    return new_config


def add_new_nginx_config(full_domain: str, port: int):
    """Create a new nginx config for the domain and add it to config folder"""
    nginx_config = generate_nginx_http_config(full_domain, port)

    file_name = full_domain + ".conf"
    new_config_path = NGINX_CONFIG_DIR / file_name

    with open(new_config_path, "w") as f:
        f.write(nginx_config)
    restart_nginx()


def remove_old_nginx_config(full_domain: str):
    file_name = full_domain + ".conf"
    old_config_path = NGINX_CONFIG_DIR / file_name

    os.unlink(old_config_path)
    restart_nginx()

# print(generate_nginx_http_config("test.example.com", 5555))