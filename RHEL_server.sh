### For Texas State University Redhat Linux Server:core-4.1-amd64:core-4.1-noarch
## Install Docker Using the Repository method
# setup the repository manager
sudo yum install -y yum-utils
sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/rhel/docker-ce.repo
# Install the docker engine
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin