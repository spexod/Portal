# One-time setup for Automatic Updates for Ubuntu cloud server
This needs to be setup once on the server to allow automatic updates
## install packages (usually these are already installed)
```
sudo apt-get install unattended-upgrades update-notifier-common
```
## enable automatic updates (this launches an interactive prompt)
See detailed in instructions: https://help.ubuntu.com/community/AutomaticSecurityUpdates

```
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

Select `yes` when the interactive prompt launch to enable updates.
THis creates a file we can open in an editor.

## open the file in an editor, to enable automatic reboots

```
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
```

Uncomment the line the about automatic reboots and set to `true`,
the final line should look like this:

```
Unattended-Upgrade::Automatic-Reboot "true";'
```

and

```
Unattended-Upgrade::Automatic-Reboot-WithUsers "true";
```

Save the file and exit.

## check the status of the automatic updates

```
apt-config dump APT::Periodic::Unattended-Upgrade
```

Which should return something like:

```
>>> APT::Periodic::Unattended-Upgrade "1";
```

Now the server will automatically update
and reboot as needed.