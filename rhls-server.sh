### For Texas State University Redhat Linux Server:core-4.1-amd64:core-4.1-noarch
## Install Docker Using the Repository method for Centos Linux
# setup the repository manager, note was are using centos as RHEL is not supported for AMD 64 architecture
sudo yum install -y yum-utils
sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo
# Install the docker engine
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin
## I needed to say 'yes' to two installation questions.
# start docker
sudo systemctl start docker
# test docker
sudo docker run hello-world
# a docker group already exists, add users, and apply the changes
sudo usermod -aG docker su-t_m170
sudo usermod -aG docker su-kqd12
newgrp docker
# now you should not need sudo to run docker, use this test to verify
docker run hello-world
# Configure Docker to start on boot
sudo systemctl enable docker.service
sudo systemctl enable containerd.service
