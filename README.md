The source code for my personal website, paulcarroll.site. Written in Python with Django. Served with Nginx and Gunicorn.

In order to deploy a change, run:

```
cd ansible
ansible-playbook -i web_servers bringup_web_server.yaml --extra-vars "code_branch=master" --tags django

# If you need to migrate the database or update static files...
ssh ubuntu@44.230.244.94
...
./migrate_environment
exit
...

# Restart everything.
ansible-playbook -i web_servers bringup_web_server.yaml --extra-vars "code_branch=master" --skip-tags django,vault
```

The current requirements.txt assumes you want Python 3.11. To install this on MacOS:

```
brew install python@3.11
brew services start postgresql@14
```

