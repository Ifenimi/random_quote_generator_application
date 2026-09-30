# Deploy to EC2

This guide deploys the Flask quote generator to an Ubuntu EC2 instance at
`16.170.220.9`, serves it through Nginx, and enables HTTPS for
`devopsghost.name.ng`.

## 1. Configure AWS and DNS

1. Launch an Ubuntu Server EC2 instance and use its key pair for SSH access.
   The commands below assume the default Ubuntu user, `ubuntu`.
2. In the instance's security group, allow inbound SSH (TCP 22) from your IP
   address, and HTTP (TCP 80) and HTTPS (TCP 443) from the internet.
3. At your DNS provider, create an **A** record for `devopsghost.name.ng` that
   points to `16.170.220.9`. Use an Elastic IP for the instance if its address
   must remain stable when stopped and started.
4. Wait until the domain resolves to the instance before requesting a TLS
   certificate. Check with `nslookup devopsghost.name.ng` from your computer.

## 2. Install server packages

Connect to the instance from PowerShell, replacing the key path as needed:

```powershell
ssh -i "$HOME\Downloads\your-key.pem" ubuntu@16.170.220.9
```

On the EC2 instance, install Python, Nginx, and Certbot, then prepare the
application directory:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx
sudo mkdir -p /opt/random-quote-generator
sudo chown ubuntu:ubuntu /opt/random-quote-generator
```

## 3. Copy the application

Open a second PowerShell window on your computer, change to the project
directory, and copy the application files. Update the key path if necessary.

```powershell
$Key = "$HOME\Downloads\your-key.pem"
scp -i $Key .\app.py .\requirements.txt ubuntu@16.170.220.9:/opt/random-quote-generator/
scp -i $Key -r .\templates .\static ubuntu@16.170.220.9:/opt/random-quote-generator/
```

Back in the EC2 SSH session, create a virtual environment and install the app
and its production server:

```bash
cd /opt/random-quote-generator
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt gunicorn
```

## 4. Run Flask with systemd and Gunicorn

Create the service definition:

```bash
sudo tee /etc/systemd/system/random-quote-generator.service >/dev/null <<'EOF'
[Unit]
Description=Random Quote Generator Flask App
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/random-quote-generator
ExecStart=/opt/random-quote-generator/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now random-quote-generator
sudo systemctl status random-quote-generator --no-pager
```

Gunicorn listens only on localhost; Nginx will accept public web traffic and
forward it to the app. Do not expose port 8000 in the EC2 security group.

## 5. Configure Nginx

Create an Nginx site that proxies requests to Gunicorn:

```bash
sudo tee /etc/nginx/sites-available/random-quote-generator >/dev/null <<'EOF'
server {
    listen 80;
    server_name devopsghost.name.ng;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/random-quote-generator /etc/nginx/sites-enabled/random-quote-generator
sudo nginx -t
sudo systemctl reload nginx
```

Before enabling HTTPS, confirm `http://devopsghost.name.ng` loads the app.

## 6. Enable HTTPS

After DNS points to the instance and HTTP is reachable, request and install a
Let's Encrypt certificate:

```bash
sudo certbot --nginx -d devopsghost.name.ng
```

Follow the prompts to provide an email address and enable HTTP-to-HTTPS
redirect. Certbot configures renewal automatically. Verify renewal with:

```bash
sudo certbot renew --dry-run
```

The site should now be available at <https://devopsghost.name.ng>.

## Operations

```bash
sudo systemctl status random-quote-generator
sudo journalctl -u random-quote-generator -n 100 --no-pager
sudo systemctl restart random-quote-generator
```

When deploying an update, copy the changed files to `/opt/random-quote-generator`
and restart the service. Keep the EC2 SSH key private, restrict SSH access to
trusted IPs, and do not run Flask's development server in production.
