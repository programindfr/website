# setup win32
```ps
python -m venv F:\etude\programmation\projetPython\FlaskRestApi\web\v3.0.x
python -m venv --upgrade --upgrade-deps F:\etude\programmation\projetPython\FlaskRestApi\web\v3.0.x
Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

# fix flask_recaptcha.py lib
in Lib\site-packages\flask_recaptcha.py, comment `from jinja2 import Markup` and add `from markupsafe import Markup`