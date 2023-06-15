# ----- Lib ----- #
from flask import (
    Blueprint,
    request,
    send_from_directory,
    abort
)
from werkzeug.utils import secure_filename
from secrets import token_urlsafe
from os import (
    mkdir,
    listdir,
    remove
)
from os.path import isdir
from json import (
    load,
    dump
)
from web_main_setup import (
    PATH,
    error500Handle,
    add_versions,
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
    global error500Handle   # ?
    tokenGET, tokenPOST = token_urlsafe(), token_urlsafe()
    mkdir(f"{PATH}/depot/{tokenGET}")
    mkdir(f"{PATH}/depot/{tokenGET}/log")
    cur.execute("INSERT INTO depot (tokenGET, tokenPOST) VALUES (?, ?)", (tokenGET, tokenPOST))
    filesVersions = {}
    allFiles = request.files.to_dict(flat=False)
    for filename in allFiles:
        for fileObject in allFiles[filename]:
            try:
                fileObject.save(f"{PATH}/depot/{tokenGET}/{secure_filename(fileObject.filename)}")
                filesVersions[secure_filename(fileObject.filename)] = add_versions("0.0.0", request.form.get(fileObject.filename))
                with open(f"{PATH}/depot/{tokenGET}/log/version.json", 'w') as f:
                    dump(filesVersions, f)
            except BaseException as err:
                blueprintDepot.logger.error(err)
                error500Handle = err    # ?
                abort(500) # trier les erreurs
    return {"tokenGET": tokenGET, "tokenPOST": tokenPOST}

@blueprintDepot.route("/<string:token>", methods=["PUT"])
def depot_PUT(token):
    global error500Handle   # ?
    cur.execute("SELECT tokenGET FROM depot WHERE tokenPOST=?", (token,))
    userData = cur.fetchall()
    if not userData:
        abort(403)
    with open(f"{PATH}/depot/{userData[0][0]}/log/version.json", 'r') as f:
        filesVersions = load(f)
    allFiles = request.files.to_dict(flat=False)
    for filename in allFiles:
        for fileObject in allFiles[filename]:
            try:
                fileObject.save(f"{PATH}/depot/{userData[0][0]}/{secure_filename(fileObject.filename)}")
                filesVersions[secure_filename(fileObject.filename)] = add_versions(
                    filesVersions[secure_filename(fileObject.filename)],
                    request.form.get(fileObject.filename)
                )
                with open(f"{PATH}/depot/{userData[0][0]}/log/version.json", 'w') as f:
                    dump(filesVersions, f)
            except BaseException as err:
                blueprintDepot.logger.error(err)
                error500Handle = err    # ?
                abort(500) # trier les erreurs
    return ('', 200)

@blueprintDepot.route("/<string:token>/<string:filename>", methods=["DELETE"])
def depot_DELETE(token, filename):
    global error500Handle   # ?
    cur.execute("SELECT tokenGET FROM depot WHERE tokenPOST=?", (token,))
    userData = cur.fetchall()
    if not userData:
        abort(403)
    with open(f"{PATH}/depot/{userData[0][0]}/log/version.json", 'r') as f:
        filesVersions = load(f)
    try:
        remove(f"{PATH}/depot/{userData[0][0]}/{secure_filename(filename)}")
        filesVersions[secure_filename(filename)] = None
        with open(f"{PATH}/depot/{userData[0][0]}/log/version.json", 'w') as f:
            dump(filesVersions, f)
    except FileNotFoundError:
        abort(404)
    except BaseException as err:
        blueprintDepot.logger.error(err)
        error500Handle = err    # ?
        abort(500)
    return ('', 200)