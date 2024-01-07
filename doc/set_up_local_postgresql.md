```
sudo apt-get update
sudo apt-get install python-pip python-dev libpq-dev postgresql postgresql-contrib
sudo su - postgres
psql
```

Then in the postgres shell:

```
CREATE DATABASE mywebsite;
CREATE USER paul WITH PASSWORD <LOCAL_DB_PASSWORD>;
ALTER ROLE paul SET client_encoding TO 'utf8';
ALTER ROLE paul SET default_transaction_isolation TO 'read committed';
ALTER ROLE paul SET timezone TO 'UTC';
ALTER ROLE paul CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE mywebsite TO paul;
\q
```

Now you should be able to migrate, assuming you are using the requirements file and
settings file from this project.

```
./manage.py migrate
./manage.py createsuperuser
```

If you want to fill your local database with the same data that is hanging out on production, then:

```
./manage.py dumpdata --database prod > /tmp/websitecontents.json
./manage.py loaddata /tmp/websitecontents.json --database local

```
