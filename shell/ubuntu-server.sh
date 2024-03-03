# install components for docker build
sudo apt-get remove docker docker-engine docker.io containerd runc
sudo apt-get -y update

sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
# install docker
sudo apt-get -y update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
# give docker sudo permissions
sudo groupadd docker # already exists?
sudo usermod -aG docker $USER
newgrp docker
# start docker on boot
sudo systemctl enable docker.service
sudo systemctl enable containerd.service

# Install Certbot for SSL certificates needed for https
sudo apt-get install snapd
sudo snap install --classic certbot
sudo mkdir /var/www
sudo mkdir /var/www/spexo

# clone the website repository
git clone https://github.com/spexod/SpExServer && cd SpExServer || return
# run the initialization script, which build and deploys the website with an http server
mkdir backend/data
sudo chmod 777 backend/data
cd backend/data || exit
git clone https://github.com/spexod/data .

docker compose up --detach

# setup a cron job to renew the SSL certificate
# get the certificate
sudo certbot certonly --webroot -w /var/www/spexo -d spexodisks.com -d www.spexodisks.com

# we now no longer need the http server, so we can get rid of it
docker compose down

 # set the environment variable to use the deployment version of NGINX server with SSL certificates
echo "NGINX_CONFIG_FILE='deploy.conf'" >> .env


# with a certificate we can now use the deployment version of the website.
shell/update.sh

# Open the crontab to setup a new cron job
sudo crontab -e
# We add a line cron tab file to check if the certificate needs to be renewed, it check once a day
0 12 * * * sudo /usr/bin/certbot renew --quiet