#!/bin/bash
# log in to the container repository on GitHub
unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac
if [ "$machine" = "Mac" ];
then
  echo -e "\nDO NOT USE 'SUDO' to run this script on a Mac,"
  echo -e "if you did, use control-c to exit, then re-run this script without 'SUDO'.\n"
  echo -e "Prepare to Enter:\n  1) Your Mac's default password\n  2) GitHub Username\n  3) Github Auth Token\n"
  read -r -p "press any key to continue..."
  security unlock-keychain
  docker login ghcr.io
else
  echo -e "\nPrepare to Enter:\n  1) GitHub Username\n  2) Github Auth Token\n"
  read -r -p "press any key to continue..."
  docker login ghcr.io
fi
