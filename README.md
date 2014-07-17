zzz
===

A blog site build with Tornado in python.

## About

zzz is just a blog site, is code in python, base on sqlite database.
It just somethings below:

- Mako
- SQLAlchemy
- Tornado
- Bootstrap

You can also see this in `requirements.txt`.

## How to run

Follow this:

- ensure virtualenv environment in your python.

- get zzz code from github.com/xiexiao/zzz.

- `virtualenv venv` build a new Python environment with virtualenv.

- `venv\Scripts\activate.bat` into the new environment in Windows. `source venv/bin/activate` when in Linux.

- `pip install -r requirements.txt` install requirements into the new environment.

- `python db_empty.py` create a empty database .

- the config.py contains cookies secret key, you must change it before deploy. 
Use 
```
import uuid; print '%s' % uuid.uuid1();
```
in Python console create a new cookies secret key.

- `python zzz.py -port=8080` run it.

- open browser and launch http://localhost:8080. 
Launch http://localhost:8080/admin for control panel, `admin` for username and `admin123` for password to login it.

## Snapshot

![zzz](https://raw.githubusercontent.com/xiexiao/zzz/master/snapshot/zzz.png)
![zzz admin](https://raw.githubusercontent.com/xiexiao/zzz/master/snapshot/zzz_admin1.png)
![zzz admin](https://raw.githubusercontent.com/xiexiao/zzz/master/snapshot/zzz_admin2.png)

