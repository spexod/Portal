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
  echo -e "\nPrepare to Enter:\n  1) Your Mac's default password\n  2) GitHub Username\n  3) Github Auth Token\n"
  read -r -p "press any key to continue..."
  security unlock-keychain
  docker login ghcr.io
else
  echo -e "\nPrepare to Enter:\n  1) GitHub Username\n  2) Github Auth Token\n"
  read -r -p "press any key to continue..."
  docker login ghcr.io
fi
