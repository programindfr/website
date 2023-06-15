# ----- Lib ----- #
from gevent import (
    monkey,
    spawn
)
monkey.patch_all()
from flask import (
    Flask,
    request,
    render_template,
    abort
)
from werkzeug.exceptions import HTTPException
from gevent.pywsgi import WSGIServer
from subprocess import getoutput
from ssl import SSLError
from web_main_setup import (
    PATH,
    CONFIG,
    __version__,
    DEBUG,
    IPADDRESS,
    PORT,
    KEYFILE,
    CERTFILE,
    error500Handle,
    build_tree,
    maclasseRegisterTmpDataThread,
    conn
)
from blueprint_qrcode import blueprintQrcode
from blueprint_depot import blueprintDepot
from blueprint_maclasse import (
    blueprintMaclasse,
    ipBan
)



# ----- Set Up ----- #
app = Flask(__name__)
app.register_blueprint(blueprintQrcode, url_prefix="/qrcode")
app.register_blueprint(blueprintDepot, url_prefix="/depot")
app.register_blueprint(blueprintMaclasse, url_prefix="/maclasse")
app.logger.setLevel(20)

# app secret key
app.secret_key = CONFIG["secret key"]

# ipban
ipBan.load_nuisances()
ipBan.url_pattern_add("/depot/", match_type="string")



# ----- Main ----- #
@app.route('/', methods=["GET"])
def index():
    return render_template(
        "index.html",
        data=request,
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

@app.route("/ip", methods=["GET"])
def ip():
    return request.__dict__["environ"]["REMOTE_ADDR"]

@app.route("/ipBanList", methods=["GET"])
def ip_ban_list():
    return ipBan.get_block_list()

@app.errorhandler(HTTPException)
def handle_exception(err):
    global error500Handle   # ?
    if err.code == 500:
        app.logger.error(f"{err.name} {error500Handle}")
        getoutput(f"""printf "{error500Handle}" | mail -s "{err.name}" -a From:{CONFIG["mail"]["error"]} {CONFIG["mail"]["dev"]}""")
        error500Handle = None   # ?
    else:
        app.logger.warning(err.name)
    return render_template(
        "handleException.html",
        err=err,
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    ), err.code

@app.errorhandler(SSLError)
def handle_ssl(err):
    app.logger.warning(err.name)
    abort(400)

spawn(SSLError).link_exception(lambda *args: app.logger.warning("spawn handle sslerror"))

@app.errorhandler(ConnectionResetError)
def handle_ssl(err):
    app.logger.warning(err.name)
    abort(400)



# ----- Launch ----- #
if __name__ == "__main__":
    try:
        app.logger.info("server start")
        print(
            "# ----- # ----- #",
            build_tree(CONFIG["directory tree"]),
            f"debug: {DEBUG}",
            f"version: {__version__}",
            f"""database name: {CONFIG["database"]["name"]}""",
            f"path: {PATH}",
            f"ip address: {IPADDRESS}",
            f"https port: {PORT}",
            "# ----- # ----- #",
            sep='\n'
        )
        maclasseRegisterTmpDataThread.start()
        https_server = WSGIServer(
            ("0.0.0.0", PORT),
            app,
            keyfile=KEYFILE,
            certfile=CERTFILE
        )
        https_server.serve_forever()
    except BaseException as err:
        app.logger.critical(err)
    finally:
        conn.close()
        app.logger.info("server stop")
