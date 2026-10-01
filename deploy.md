# Deploy to Amazon EC2

This guide deploys the Flask quote generator to the following server and domain:

- **Server IP:** `16.170.220.9`
- **Domain:** `devopsghost.name.ng`
- **Application port:** `8000` internally, proxied through Nginx

The commands below assume an Ubuntu EC2 instance and a local clone of this repository.

## 1. Configure AWS networking

In the EC2 security group attached to `16.170.220.9`, allow inbound traffic for:

- SSH, TCP `22`, from your own IP address
- HTTP, TCP `80`, from `0.0.0.0/0`
- HTTPS, TCP `443`, from `0.0.0.0/0`

Do not expose port `8000` publicly. Gunicorn will listen only on the server itself.

## 2. Point the domain to EC2

At the DNS provider for `name.ng`, create or update this record:

| Type | Name          | Value          | TTL   |
| ---- | ------------- | -------------- | ----- |
| A    | `devopsghost` | `16.170.220.9` | `300` |

Wait until the record resolves before requesting the SSL certificate. You can check it with:

```bash
nslookup devopsghost.name.ng
```

## 3. Connect to the server

Replace `<KEY_PATH>` with the path to your private key and `<EC2_USER>` with the AMI username, commonly `ubuntu` for Ubuntu Linux.

```bash
ssh -i <KEY_PATH> <EC2_USER>@16.170.220.9
```

Update the operating system and install the runtime packages:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip nginx
```

## 4. Copy and prepare the application

From PowerShell on your local machine, run these commands from the repository directory. Set the key path and EC2 username as above. These commands copy only application files, not the local Windows `.venv`.

```powershell
$KeyPath = "$HOME\Downloads\your-key.pem"
scp -i $KeyPath .\app.py .\requirements.txt .\test_app.py <EC2_USER>@16.170.220.9:/home/<EC2_USER>/
scp -i $KeyPath -r .\templates .\static <EC2_USER>@16.170.220.9:/home/<EC2_USER>/
```

Back on the EC2 server, install the application under `/var/www`:

```bash
sudo mkdir -p /var/www/random-quote-generator-python-app
sudo cp /home/$USER/app.py /home/$USER/requirements.txt /home/$USER/test_app.py /var/www/random-quote-generator-python-app/
sudo cp -r /home/$USER/templates /home/$USER/static /var/www/random-quote-generator-python-app/
sudo chown -R $USER:www-data /var/www/random-quote-generator-python-app
cd /var/www/random-quote-generator-python-app
```

Create the virtual environment and install the production dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Run the tests before starting the service:

```bash
.venv/bin/python -m unittest discover -v
```

To check the app locally on the EC2 instance, run the development server bound to localhost:

```bash
.venv/bin/flask --app app run --host=127.0.0.1 --port=5000
```

In another SSH session, check `curl http://127.0.0.1:5000`, then stop the development server with `Ctrl+C` before continuing.

## 5. Create the systemd service

Create the service file:

```bash
sudo vim /etc/systemd/system/random-quote-generator.service
```

Paste this configuration:

```ini
[Unit]
Description=Random Quote Generator Flask application
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/random_quote_generator_application
Environment="PATH=/var/www/random_quote_generator_application/.venv/bin"
ExecStart=/var/www/random_quote_generator_application/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

If the EC2 login user is not `ubuntu`, change `User=ubuntu` and use that user in the ownership command above. Keep `Group=www-data` so the service runs with the Nginx group.

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now random-quote-generator
sudo systemctl status random-quote-generator
```

The service should show `active (running)`. If it does not, inspect the logs:

```bash
sudo journalctl -u random-quote-generator -n 50 --no-pager
```

## 6. Configure Nginx

Create an Nginx site configuration:

```bash
sudo vim /etc/nginx/sites-available/random-quote-generator
```

Paste:

```nginx
server {
   listen 80;
   listen [::]:80;

   server_name 16.170.220.9 devopsghost.name.ng;

   location / {
      proxy_pass http://127.0.0.1:8000;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
   }
}
```

Enable the site and verify the configuration:

```bash
sudo ln -s /etc/nginx/sites-available/random-quote-generator /etc/nginx/sites-enabled/random-quote-generator
sudo nginx -t
sudo systemctl reload nginx
```

Visit `http://devopsghost.name.ng` to confirm that the application loads.

## 7. Enable HTTPS with Let's Encrypt

Install Certbot and its Nginx plugin:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Request and install the certificate:

```bash
sudo certbot --nginx -d devopsghost.name.ng
```

Choose the option to redirect HTTP traffic to HTTPS when prompted. Confirm automatic renewal with:

```bash
sudo certbot renew --dry-run
```

The application should now be available at:

```text
https://devopsghost.name.ng
```

## Updating the application

From PowerShell in the local repository, copy the changed files to the EC2 instance. Include `templates` or `static` if either directory changed:

```powershell
scp -i $KeyPath .\app.py .\requirements.txt .\test_app.py <EC2_USER>@16.170.220.9:/var/www/random-quote-generator-python-app/
scp -i $KeyPath -r .\templates .\static <EC2_USER>@16.170.220.9:/var/www/random-quote-generator-python-app/
```

Then run on EC2:

```bash
cd /var/www/random-quote-generator-python-app
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -v
sudo systemctl restart random-quote-generator
sudo systemctl status random-quote-generator
```

To watch application logs while troubleshooting:

```bash
sudo journalctl -u random-quote-generator -f
```
