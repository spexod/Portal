 # install components for docker build
 sudo apt-get remove docker docker-engine docker.io containerd runc
 sudo apt-get -y update
  sudo apt-get -y install \
     ca-certificates \
     curl \
     gnupg \
     lsb-release
 curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
 echo \
   "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
 # install docker
 sudo apt-get -y update
 sudo apt-get -y install docker-ce docker-ce-cli containerd.io
 # give docker sudo permissions
 sudo groupadd docker # already exists?
 sudo usermod -aG docker $USER
 newgrp docker
 # start docker on boot
 sudo systemctl enable docker.service
 sudo systemctl enable containerd.service
 # install docker-compose
 sudo apt -y install docker-compose

 # Install Certbot for SSL certificates needed for https
 sudo apt-get install snapd
 sudo snap install --classic certbot
 sudo mkdir /var/www
 sudo mkdir /var/www/spexo

 # clone the website repository
 git clone https://github.com/spexod/SpExServer && cd SpExServer || return
 # run the initialization script, which build and deploys the website with an http server
 ./init.sh

 # setup a cron job to renew the SSL certificate
 # get the certificate
 sudo certbot certonly --webroot -w /var/www/spexo -d spexodisks.com -d www.spexodisks.com

 # we now no longer need the http server, so we can get rid of it
 docker compose down

 # set the environment variable to use the deployment version of NGINX server with SSL certificates
  echo "NGINX_CONFIG_FILE='deploy.conf'" >> .env
 echo "NGINX_CONFIG_FILE='deploy.conf'" >> .env

 # with a certificate we can now use the deployment version of the website.
 ./update-deploy.sh

 # Open the crontab to setup a new cron job
 sudo crontab -e
 # We add a line cron tab file to check if the certificate needs to be renewed, it check once a day
 0 12 * * * sudo /usr/bin/certbot renew --quiet