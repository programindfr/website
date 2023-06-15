# ----- Lib ----- #
from gevent import (
    monkey,
    spawn
)
monkey.patch_all()
from flask import (
    Blueprint,
    Flask,
    request,
    render_template,
    redirect,
    send_from_directory,
    make_response,
    abort
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from flask_recaptcha import ReCaptcha
from gevent.pywsgi import WSGIServer
from subprocess import getoutput
from flask_ipban import IpBan
from secrets import (
    token_urlsafe,
    token_hex
)
from os import (
    mkdir,
    listdir,
    walk,
    rename,
    remove,
    rmdir
)
from os.path import (
    isdir,
    isfile,
    join as osjoin,
    islink,
    getsize
)
from qrcode import make
from sys import platform
from datetime import (
    datetime,
    timedelta
)
from time import sleep
from threading import (
    Thread,
    current_thread
)
from json import (
    load,
    dump
)
from ssl import SSLError
from web_main_setup import (
    OS,
    check_path,
    PATH,
    CONFIG,
    __version__,
    DEBUG,
    IPADDRESS,
    PORT,
    KEYFILE,
    CERTFILE,
    HTMLMAIL,
    maclasseRegisterTmpData,
    error500Handle,
    build_tree,
    send_mail,
    add_versions,
    maclasseRegisterTmpDataThread,
    conn,
    cur
)



# ----- Set Up ----- #
blueprintDepot = Blueprint("blueprintDepot", __name__)
blueprintDepot.logger.setLevel(20)



# ----- Depot ----- #
@blueprintDepot.route("/<string:token>/<path:filename>", methods=["GET"])
def depot_GET(token, filename):
    if token in [d for d in listdir(f"{PATH}/depot") if isdir(f"{PATH}/depot/{d}")]:
        return send_from_directory(f"{PATH}/depot/{token}", filename)
    abort(403)

@blueprintDepot.route("/", methods=["POST"])
def depot_POST():
    global error500Handle
    tokenGET, tokenPOST = token_urlsafe(), token_urlsafe()
    mkdir(f"{PATH}/depot/{tokenGET}")
    mkdir(f"{PATH}/depot/{tokenGET}/log")
    cur.execute("INSERT INTO depot (tokenGET, tokenPOST) VALUES (?, ?)", (tokenGET, tokenPOST))
    filesVersions = {}
    allFiles = request.files.to_dict(flat=False)
    for filename in allFiles:
        for fileObject in allFiles[filename]:
            try:
                fileObject.save(check_path(f"{PATH}/depot/{tokenGET}/{secure_filename(fileObject.filename)}"))
                filesVersions[secure_filename(fileObject.filename)] = add_versions("0.0.0", request.form.get(fileObject.filename))
                with open(check_path(f"{PATH}/depot/{tokenGET}/log/version.json"), 'w') as f:
                    dump(filesVersions, f)
            except BaseException as err:
                app.logger.error(err)
                error500Handle = err
                abort(500) # trier les erreurs
    return {"tokenGET": tokenGET, "tokenPOST": tokenPOST}

@app.route("/<string:token>", methods=["PUT"])
def depot_PUT(token):
    global error500Handle
    cur.execute("SELECT tokenGET FROM depot WHERE tokenPOST=?", (token,))
    userData = cur.fetchall()
    if not userData:
        abort(403)
    with open(check_path(f"{PATH}/depot/{userData[0][0]}/log/version.json"), 'r') as f:
        filesVersions = load(f)
    allFiles = request.files.to_dict(flat=False)
    for filename in allFiles:
        for fileObject in allFiles[filename]:
            try:
                fileObject.save(check_path(f"{PATH}/depot/{userData[0][0]}/{secure_filename(fileObject.filename)}"))
                filesVersions[secure_filename(fileObject.filename)] = add_versions(
                    filesVersions[secure_filename(fileObject.filename)],
                    request.form.get(fileObject.filename)
                )
                with open(check_path(f"{PATH}/depot/{userData[0][0]}/log/version.json"), 'w') as f:
                    dump(filesVersions, f)
            except BaseException as err:
                app.logger.error(err)
                error500Handle = err
                abort(500) # trier les erreurs
    return ('', 200)

@app.route("/<string:token>/<string:filename>", methods=["DELETE"])
def depot_DELETE(token, filename):
    global error500Handle
    cur.execute("SELECT tokenGET FROM depot WHERE tokenPOST=?", (token,))
    userData = cur.fetchall()
    if not userData:
        abort(403)
    with open(check_path(f"{PATH}/depot/{userData[0][0]}/log/version.json"), 'r') as f:
        filesVersions = load(f)
    try:
        remove(check_path(f"{PATH}/depot/{userData[0][0]}/{secure_filename(filename)}"))
        filesVersions[secure_filename(filename)] = None
        with open(check_path(f"{PATH}/depot/{userData[0][0]}/log/version.json"), 'w') as f:
            dump(filesVersions, f)
    except FileNotFoundError:
        abort(404)
    except BaseException as err:
        app.logger.error(err)
        error500Handle = err
        abort(500)
    return ('', 200)