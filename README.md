The project is not longer windows compatible.
This projet is an upgrade of my actual website so the code is not working yet.

# setup
```bash
python -m venv .
python -m venv --upgrade --upgrade-deps .
source bin/activate
python -m pip install -r requirements.txt
```

# exit
```bash
deactivate
```

# fix flask_recaptcha.py lib
in `lib/python3.x/site-packages/flask_recaptcha.py`, comment `from jinja2 import Markup` and add `from markupsafe import Markup`

# Requirements
- [installing mariadb connectorc](https://mariadb.com/kb/en/about-mariadb-connector-c/#installing-mariadb-connectorc-on-linux)
- [setup mail server](https://raspberrytips.com/mail-server-raspberry-pi/)