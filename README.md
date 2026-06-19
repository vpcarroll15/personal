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
ansible-playbook -i web_servers bringup_web_server.yaml --extra-vars "code_branch=master" --skip-tags vault
```

This will deploy the code, run migrations, collect static files, and restart all services.

The current requirements.txt assumes you want Python 3.12. To install this on MacOS:

```
brew install python@3.12
brew services start postgresql@16
```

## Dependencies

Dependencies are split into two files, and both pin only **direct** dependencies (transitive
dependencies are left for pip to resolve, so version bumps don't conflict with stale transitive
pins):

- `requirements.txt` — runtime dependencies for the web app and the `twilio_managers` daemons. This
  is what the server installs (the ansible playbook installs it automatically).
- `requirements-dev.txt` — `requirements.txt` plus dev/test/ops tooling (ansible, linters, coverage,
  freezegun, ipython, etc.). Use this locally.

For local development:

```
pip install -r requirements-dev.txt
```
