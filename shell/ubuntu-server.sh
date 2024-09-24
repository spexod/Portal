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
# clone the website repository
git clone https://github.com/spexod/Portal && cd Portal || exit
# run the initialization script, which build and deploys the website with an http server
./shell/init.sh
# see https://github.com/spexod/Portal/shell/ssl.md for the next steps