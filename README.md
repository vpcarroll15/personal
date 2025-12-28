The source code for my personal website, paulcarroll.site. Written in Python with Django. Served
with Nginx and Gunicorn.

If you're setting up a new server, make sure to `sudo apt update && sudo apt upgrade` first.

Other new server notes:

- You'll need to run some basic commands to create the Postgres database and the right user.
- Make a dump of the old Postgres database and transfer the dump to the new instance.
- You won't need to run any Django migrations. (In fact you definitely don't want to.) Applying the
  dump will take care of everything.
- Make sure that the Django owner ends up owning everything, not postgres.

NOTE: last time you set up a new server, you had to do this to make sure that nginx could actually
read and share the static assets:

```
# Give nginx user access to your home directory and static files
sudo chmod 755 /home/ubuntu/
sudo chmod 755 /home/ubuntu/source/
sudo chmod -R 755 /home/ubuntu/source/static/
```

In order to deploy a change, run:

```
cd ansible
ansible-playbook -i web_servers bringup_web_server.yaml --extra-vars "code_branch=master" --tags django

# If you need to migrate the database or update static files...
ssh ubuntu@hostname
...
./migrate_environment
exit
...

# Restart everything.
ansible-playbook -i web_servers bringup_web_server.yaml --extra-vars "code_branch=master" --skip-tags django,vault
```

The current requirements.txt assumes you want Python 3.12. To install this on MacOS:

```
brew install python@3.12
brew services start postgresql@16
```
