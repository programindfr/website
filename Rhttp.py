# ----- Lib ----- #
from gevent import monkey
monkey.patch_all()
from flask import (
    Flask,
    redirect,
    send_from_directory
)
from gevent.pywsgi import WSGIServer
from flask_ipban import IpBan
from yaml import safe_load
from os.path import isdir
from os import (
    mkdir,
    listdir
)
from sys import platform
from werkzeug.exceptions import HTTPException



# ----- Set Up ----- #
app = Flask(__name__)
app.logger.setLevel(20)

# yaml config
OS = platform
check_path = lambda x: x.replace('/', '\\') if OS == "win32" else x
if OS == "win32":
    PATH = '\\'.join(__file__.split('\\')[:-1])
else:
    PATH = '/'.join(__file__.split('/')[:-1])
with open(check_path(f"{PATH}/config.yaml"), 'r') as config_file:
    CONFIG = safe_load(config_file)

# app secret key
app.secret_key = CONFIG["secret key"]

# const var
DEBUG = CONFIG["debug"]
if DEBUG:
    IPADDRESS = CONFIG[f"debug {OS}"]["ip address"]
    PORT = CONFIG[f"debug {OS}"]["http port"]
else:
    IPADDRESS = CONFIG[f"prod {OS}"]["ip address"]
    PORT = CONFIG[f"prod {OS}"]["http port"]

# ipban
ipBan = IpBan(app, persist=not CONFIG["debug"], ipc=True)
ipBan.load_nuisances()



# ----- Def ----- #
def build_certbot_dir():
    dirList = [f for f in listdir(check_path(PATH)) if isdir(check_path(f"{PATH}/{f}"))]
    if not ".well-known" in dirList:
        mkdir(check_path(f"{PATH}/.well-known"))



# ----- Main ----- #
@app.route('/')
def index():
    return redirect(f"https://{IPADDRESS}")

@app.route("/.well-known/<path:path>", methods=["GET"])
def certbot(path):
    build_certbot_dir()
    return send_from_directory(
        check_path(f"{PATH}/.well-known"),
        path
    )

@app.errorhandler(HTTPException)
def handle_exception(err):
    app.logger.warning(f"{err.code} {err.name}")
    return redirect(f"https://{IPADDRESS}")



# ----- Launch ----- #
if __name__ == "__main__":
    try:
        http_server = WSGIServer(("0.0.0.0", PORT), app)
        http_server.serve_forever()
    except BaseException as err:
        app.logger.critical(err)
    finally:
        pass
