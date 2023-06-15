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
from blueprint_qrcode import blueprintQrcode
from blueprint_depot import blueprintDepot



# ----- Set Up ----- #
app = Flask(__name__)
app.register_blueprint(blueprintQrcode, url_prefix="/qrcode")
app.register_blueprint(blueprintDepot, url_prefix="/depot")
app.logger.setLevel(20)

# app secret key
app.secret_key = CONFIG["secret key"]

# reCAPTCHA site/secret keys
app.config["RECAPTCHA_SITE_KEY"] = CONFIG["recaptcha"]["site key"]
app.config["RECAPTCHA_SECRET_KEY"] = CONFIG["recaptcha"]["secret key"]
recaptcha = ReCaptcha(app)

# ipban
ipBan = IpBan(
    app,
    ban_count=10,
    ban_seconds=3600*24*7,
    persist=not DEBUG,
    ipc=True
)
ipBan.load_nuisances()
ipBan.url_pattern_add("/maclasse/login", match_type="string")
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
    global error500Handle
    if err.code == 500:
        app.logger.error(f"{err.name} {error500Handle}")
        getoutput(f"""printf "{error500Handle}" | mail -s "{err.name}" -a From:{CONFIG["mail"]["error"]} {CONFIG["mail"]["dev"]}""")
        error500Handle = None
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





# depot API
@app.route("/depot/<string:token>/<path:filename>", methods=["GET"])
def depot_GET(token, filename):
    if token in [d for d in listdir(check_path(f"{PATH}/depot")) if isdir(check_path(f"{PATH}/depot/{d}"))]:
        return send_from_directory(check_path(f"{PATH}/depot/{token}"), filename)
    abort(403)

@app.route("/depot", methods=["POST"])
def depot_POST():
    global error500Handle
    tokenGET, tokenPOST = token_urlsafe(), token_urlsafe()
    mkdir(check_path(f"{PATH}/depot/{tokenGET}"))
    mkdir(check_path(f"{PATH}/depot/{tokenGET}/log"))
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

@app.route("/depot/<string:token>", methods=["PUT"])
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

@app.route("/depot/<string:token>/<string:filename>", methods=["DELETE"])
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


# maclasse
# main page -> GET to show files/folders, POST to upload files/create folders -> main page
@app.route("/maclasse/index/", defaults={"path": ''}, methods=["GET"])
@app.route("/maclasse/index/<path:path>", methods=["GET"])
def maclasse_GET(path):
    token = request.cookies.get("token")
    cur.execute("SELECT folder, accessLock, title, bgPic, color FROM maclasse WHERE token=?", (token,))
    userData = cur.fetchall()
    if not userData:
        return redirect("/maclasse/login")
    oldFilename = request.args.get("rename")
    isProf = bool(request.cookies.get("isProf"))
    try:
        filesNames = [f for f in listdir(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}")) if isfile(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}/{f}"))]
        dirsNames = [f for f in listdir(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}")) if isdir(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}/{f}"))]
    except BaseException as err:
        app.logger.error(err)
        abort(404)
    total_size = 0
    for dirpath, dirnames, filenames in walk(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}")):
        for f in filenames:
            fp = osjoin(dirpath, f)
            if not islink(fp):
                total_size += getsize(fp)
    finalSize = lambda size: f"{int(size/1_000_000_000)}GB" if (size/1_000_000_000) > 1 else f"{int(size/1_000_000)}MB" if (size/1_000_000) > 1 else f"{int(size/1_000)}KB" if (size/1_000) > 1 else f"{size}B"
    return render_template(
        "maclasse.html",
        filesNames=sorted(filesNames),
        dirsNames=sorted(dirsNames),
        path=path,
        size=finalSize(total_size),
        isProf=isProf,
        accessLock=userData[0][1],
        oldFilename=oldFilename,
        title=userData[0][2],
        bgPic=userData[0][3],
        color=userData[0][4],
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

@app.route("/maclasse/index/", defaults={"path": ''}, methods=["POST"])
@app.route("/maclasse/index/<path:path>", methods=["POST"])
def maclasse_POST(path):
    global error500Handle
    token = request.cookies.get("token")
    cur.execute("SELECT folder, accessLock, title, bgPic, color FROM maclasse WHERE token=?", (token,))
    userData = cur.fetchall()
    if not userData:
        return redirect("/maclasse/login")
    if bool(request.args.get("file")):
        for fileObject in request.files.to_dict(flat=False)["file"]:
            try:
                fileObject.save(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}{secure_filename(fileObject.filename)}"))
            except BaseException as err:
                app.logger.error(err)
                error500Handle = err
                abort(500) # trier les erreurs
    if bool(request.args.get("dir")):
        dirName = request.form["dirName"]
        mkdir(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}{dirName}"))
    if bool(request.args.get("oldFilename")):
        newFilename = secure_filename(request.form["newFilename"])
        fileExt = secure_filename(request.args.get("oldFilename")).split('.')[-1]
        oldFilename = '.'.join(secure_filename(request.args.get("oldFilename")).split('.')[:-1])
        try:
            rename(
                check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}{oldFilename}.{fileExt}"),
                check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}{newFilename}.{fileExt}")
            )
            cur.execute("SELECT picId FROM maclasseShareDict WHERE path=?", (
                f"{userData[0][0]}/{path}{oldFilename}.{fileExt}",
            ))
            maclasseShareDict = cur.fetchall()
            if maclasseShareDict:
                cur.execute("UPDATE maclasseShareDict SET path=? WHERE picId=?", (
                    f"{userData[0][0]}/{path}{newFilename}.{fileExt}",
                    maclasseShareDict[0][0]
                ))
        except BaseException as err:
                app.logger.error(err)
                error500Handle = err
                abort(500) # trier les erreurs
    if request.args.get("lock") and bool(request.cookies.get("isProf")):
        cur.execute("UPDATE maclasse SET accessLock=? WHERE folder=?", (
            bool(int(request.args.get("lock"))),
            userData[0][0]
        ))
    if bool(request.args.get("newTitle")) and bool(request.cookies.get("isProf")):
        cur.execute("UPDATE maclasse SET title=? WHERE folder=?", (
            request.form["newTitle"],
            userData[0][0]
        ))
    if bool(request.args.get("bgPic")) and bool(request.cookies.get("isProf")):
        for fileObject in request.files.to_dict(flat=False)["bgPic"]:
            try:
                fileName = f"{userData[0][0]}.{secure_filename(fileObject.filename).split('.')[-1]}"
                fileObject.save(check_path(f"{PATH}/maclasse/custom/{fileName}"))
                cur.execute("UPDATE maclasse SET bgPic=? WHERE folder=?", (
                    fileName,
                    userData[0][0]
                ))
            except BaseException as err:
                app.logger.error(err)
                error500Handle = err
                abort(500) # trier les erreurs
    if bool(request.args.get("color")) and bool(request.cookies.get("isProf")):
        cur.execute("UPDATE maclasse SET color=? WHERE folder=?", (
            request.form["color"],
            userData[0][0]
        ))
    return redirect(f"/maclasse/index/{path}")

# maclasse global download page
@app.route("/maclasse/dl/<path:path>", methods=["GET"])
def maclasse_dl(path):
    rootDirectory = request.args.get('r')
    if rootDirectory == "cloud":
        token = request.cookies.get("token")
        cur.execute("SELECT folder FROM maclasse WHERE token=?", (token,))
        userData = cur.fetchall()
        if not userData:
            abort(401)
        isProf = bool(request.cookies.get("isProf"))
        if not isProf:
            abort(403)
        return send_from_directory(
            check_path(f"{PATH}/maclasse/{rootDirectory}/{userData[0][0]}/{'/'.join(path.split('/')[:-1])}"),
            path.split('/')[-1]
        )
    elif rootDirectory == "pictures":
        picId = path
        return send_from_directory(
            check_path(f"{PATH}/maclasse/{rootDirectory}"),
            f"{picId}.png"
        )
    elif rootDirectory == "share":
        picId = path
        cur.execute("SELECT path FROM maclasseShareDict WHERE picId=?", (picId,))
        maclasseShareDict = cur.fetchall()
        if not maclasseShareDict:
            abort(404)
        return send_from_directory(
            check_path(f"{PATH}/maclasse/cloud/{'/'.join(maclasseShareDict[0][0].split('/')[:-1])}"),
            maclasseShareDict[0][0].split('/')[-1],
            download_name=f"{picId}.{maclasseShareDict[0][0].split('.')[-1]}"
        )
    elif rootDirectory == "custom":
        bgPic = path
        return send_from_directory(
            check_path(f"{PATH}/maclasse/{rootDirectory}"),
            bgPic
        )
    else:
        abort(404)


# delete files/folders page -> GET to delete files/folders from html main page -> main page
@app.route("/maclasse/delete/<path:path>", methods=["GET"])
def maclasse_delete(path):
    token = request.cookies.get("token")
    cur.execute("SELECT folder FROM maclasse WHERE token=?", (token,))
    userData = cur.fetchall()
    if not userData:
        abort(401)
    isProf = bool(request.cookies.get("isProf"))
    if not isProf:
        abort(403)
    if bool(request.args.get("file")):
        remove(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}"))
    if bool(request.args.get("dir")):
        try:
            rmdir(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}"))
        except OSError as err:
            app.logger.error(err)
            global error500Handle
            error500Handle = err
            abort(500) # trier les erreurs
    finalPath = lambda: '/'.join(path.split('/')[:-1]) + '/' if len(path.split('/'))>1 else ''
    return redirect(f"/maclasse/index/{finalPath()}")

# login page -> GET to show html, POST to verify html -> main page/login page
@app.route("/maclasse/login", methods=["GET"])
def maclasse_login_GET():
    return render_template(
        "maclasseLogin.html",
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

@app.route("/maclasse/login", methods=["POST"])
def maclasse_login_POST():
    if recaptcha.verify():
        cur.execute("SELECT token, pw, profPw, accessLock FROM maclasse WHERE id=?", (request.form["id"],))
        userData = cur.fetchall()
        if userData:
            if check_password_hash(userData[0][1], request.form["pw"]):
                if not bool(userData[0][3]):
                    resp = make_response(redirect("/maclasse/index/"))
                    if bool(request.form.get("keepConnect")):
                        resp.set_cookie(
                            "token",
                            userData[0][0],
                            max_age=3600*24*365,
                            secure=True,
                            httponly=True,
                            samesite="lax"
                        ) # secure=True avec https
                    else:
                        resp.set_cookie(
                            "token",
                            userData[0][0],
                            secure=True,
                            httponly=True,
                            samesite="lax"
                        ) # secure=True avec https
                    return resp
                return render_template(
                    "maclasseLogin.html",
                    warn="L'accès a été révoqué par le professeur.",
                    websiteName=CONFIG["website name"],
                    version=__version__,
                    contactMail=CONFIG["mail"]["contact"]
                )
            elif check_password_hash(userData[0][2], request.form["pw"]):
                resp = make_response(redirect("/maclasse/index/"))
                if bool(request.form.get("keepConnect")):
                    resp.set_cookie(
                        "token",
                        userData[0][0],
                        max_age=3600*24*365,
                        secure=True,
                        httponly=True,
                        samesite="lax"
                    ) # secure=True avec https
                    resp.set_cookie(
                        "isProf",
                        '1',
                        max_age=3600*24*365,
                        secure=True,
                        httponly=True,
                        samesite="lax"
                    ) # secure=True avec https
                else:
                    resp.set_cookie(
                        "token",
                        userData[0][0],
                        secure=True,
                        httponly=True,
                        samesite="lax"
                    ) # secure=True avec https
                    resp.set_cookie(
                        "isProf",
                        '1',
                        secure=True,
                        httponly=True,
                        samesite="lax"
                    ) # secure=True avec https
                return resp
        return render_template(
            "maclasseLogin.html",
            warn="Identifiant et/ou mot de passe incorrect.",
            websiteName=CONFIG["website name"],
            version=__version__,
            contactMail=CONFIG["mail"]["contact"]
        )
    ipBan.add()
    return render_template(
        "maclasseLogin.html",
        warn="Le reCAPTCHA est obligatoire.",
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

# logout page -> GET to logout -> index website page
@app.route("/maclasse/logout", methods=["GET"])
def maclasse_logout():
    resp = make_response(redirect("/maclasse/login"))
    resp.set_cookie("token", '', max_age=0)
    resp.set_cookie("isProf", '0', max_age=0)
    return resp

# register page -> GET to show html, POST to verify html -> register page/login page
@app.route("/maclasse/register", methods=["GET"])
def maclasse_register_GET():
    if bool(request.args.get("m")):
        return render_template(
            "maclasseRegisterCheck.html",
            websiteName=CONFIG["website name"],
            version=__version__,
            contactMail=CONFIG["mail"]["contact"]
        )
    return render_template(
        "maclasseRegister.html",
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

@app.route("/maclasse/register", methods=["POST"])
def maclasse_register_POST():
    pageCode = request.form.get("code")
    if bool(pageCode):
        if recaptcha.verify():
            if pageCode in maclasseRegisterTmpData:
                cur.execute(
                    """INSERT INTO maclasse (
                        token,
                        id,
                        pw,
                        profPw,
                        accessLock,
                        title,
                        bgPic,
                        color
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
                        maclasseRegisterTmpData[pageCode]["token"],
                        maclasseRegisterTmpData[pageCode]["id"],
                        maclasseRegisterTmpData[pageCode]["pw"],
                        maclasseRegisterTmpData[pageCode]["profPw"],
                        maclasseRegisterTmpData[pageCode]["accessLock"],
                        maclasseRegisterTmpData[pageCode]["title"],
                        maclasseRegisterTmpData[pageCode]["bgPic"],
                        maclasseRegisterTmpData[pageCode]["color"]
                    )
                )
                cur.execute("SELECT folder FROM maclasse WHERE id=?", (maclasseRegisterTmpData[pageCode]["id"],))
                userData = cur.fetchall()
                mkdir(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}"))
                del maclasseRegisterTmpData[pageCode]
                return redirect("/maclasse/login")
            return render_template(
                "maclasseRegisterCheck.html",
                warn="Ce code n'est pas valide.",
                websiteName=CONFIG["website name"],
                version=__version__,
                contactMail=CONFIG["mail"]["contact"]
            )
        ipBan.add()
        return render_template(
            "maclasseRegisterCheck.html",
            warn="Le reCAPTCHA est obligatoire.",
            websiteName=CONFIG["website name"],
            version=__version__,
            contactMail=CONFIG["mail"]["contact"]
        )
    elif recaptcha.verify():
        if "@ac-" in request.form["email"]:
            if request.form["pw"] == request.form["pw2"] and request.form["profPw"] == request.form["profPw2"]:
                if request.form["pw"] != request.form["profPw"]:
                    cur.execute("SELECT id FROM maclasse")
                    for userId in cur.fetchall():
                        if request.form["id"] == userId[0]:
                            return render_template(
                                "maclasseRegister.html",
                                warn="Cet identifiant est déjà pris.",
                                websiteName=CONFIG["website name"],
                                version=__version__,
                                contactMail=CONFIG["mail"]["contact"]
                            )
                    mailCode = token_hex(4)
                    send_mail({"mailCode": mailCode, "contactMail": CONFIG["mail"]["contact"], "ipAddress": IPADDRESS, "websiteName": CONFIG["website name"]}, HTMLMAIL, "Code de vérification", CONFIG["mail"]["noreply"], request.form["email"])
                    maclasseRegisterTmpData[mailCode] = {
                        "token": token_urlsafe(),
                        "id": request.form["id"],
                        "pw": generate_password_hash(request.form["pw"]),
                        "profPw": generate_password_hash(request.form["profPw"]),
                        "accessLock": 0,
                        "title": '',
                        "bgPic": '',
                        "color": '',
                        "date": datetime.now()
                    }
                    return render_template(
                        "maclasseRegisterCheck.html",
                        websiteName=CONFIG["website name"],
                        version=__version__,
                        contactMail=CONFIG["mail"]["contact"]
                    )
                return render_template(
                    "maclasseRegister.html",
                    warn="Le mot de passe élève et professeur ne doivent pas être identiques.",
                    websiteName=CONFIG["website name"],
                    version=__version__,
                    contactMail=CONFIG["mail"]["contact"]
                )
            return render_template(
                "maclasseRegister.html",
                warn="Le mot de passe et sa confirmation doivent être identiques.",
                websiteName=CONFIG["website name"],
                version=__version__,
                contactMail=CONFIG["mail"]["contact"]
            )
        return render_template(
                "maclasseRegister.html",
                warn="L'adresse mail doit être une adresse mail académique.",
                websiteName=CONFIG["website name"],
                version=__version__,
                contactMail=CONFIG["mail"]["contact"]
            )
    ipBan.add()
    return render_template(
        "maclasseRegister.html",
        warn="Le reCAPTCHA est obligatoire.",
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

@app.route("/maclasse/share/<path:path>", methods=["GET"])
def maclasse_share_GET(path):
    picId = path
    cur.execute("SELECT path FROM maclasseShareDict WHERE picId=?", (
        picId,
    ))
    maclasseShareDict = cur.fetchall()
    if not maclasseShareDict:
        abort(404)
    cur.execute("SELECT title, bgPic, color FROM maclasse WHERE folder=?", (
        maclasseShareDict[0][0].split('/')[0],
    ))
    userData = cur.fetchall()
    return render_template(
        "maclasseDisplayShare.html",
        picId=picId,
        title=userData[0][0],
        bgPic=userData[0][1],
        color=userData[0][2],
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

@app.route("/maclasse/share/<path:path>", methods=["POST"])
def maclasse_share_POST(path):
    token = request.cookies.get("token")
    cur.execute("SELECT folder, title, bgPic, color FROM maclasse WHERE token=?", (token,))
    userData = cur.fetchall()
    if not userData:
        abort(401)
    cur.execute("SELECT picId FROM maclasseShareDict WHERE path=?", (
        f"{userData[0][0]}/{path}",
    ))
    maclasseShareDict = cur.fetchall()
    if not maclasseShareDict:
        picId = token_urlsafe()
        ext = path.split('.')[-1]
        if ext in CONFIG["audio"]:
            pathWithoutExt = '.'.join(path.split('.')[:-1])
            if OS == "win32":
                getoutput(f"""{check_path(PATH + '/' + CONFIG[f"debug win32"]["ffmpeg path"])} -i {check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}")} {check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{pathWithoutExt}.mp3")}""")
            else:
                getoutput(f"""ffmpeg -i {f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}"} {f"{PATH}/maclasse/cloud/{userData[0][0]}/{pathWithoutExt}.mp3"}""")
            remove(check_path(f"{PATH}/maclasse/cloud/{userData[0][0]}/{path}"))
            cur.execute("INSERT INTO maclasseShareDict (picId, path) VALUES (?, ?)", (
                picId,
                f"{userData[0][0]}/{pathWithoutExt}.mp3"
            ))
        else:
            cur.execute("INSERT INTO maclasseShareDict (picId, path) VALUES (?, ?)", (
                picId,
                f"{userData[0][0]}/{path}"
            ))
        make(f"https://{IPADDRESS}/maclasse/share/{picId}").save(check_path(f"{PATH}/maclasse/pictures/{picId}.png"))
    else:
        picId = maclasseShareDict[0][0]
    return render_template(
        "maclasseShare.html",
        id=picId,
        title=userData[0][1],
        bgPic=userData[0][2],
        color=userData[0][3],
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

@app.route("/maclasse/access", methods=["GET"])
def maclasse_access():
    token = request.cookies.get("token")
    cur.execute("SELECT folder FROM maclasse WHERE token=?", (token,))
    userData = cur.fetchall()
    if not userData:
        abort(401)
    isProf = bool(request.cookies.get("isProf"))
    if not isProf:
        abort(403)
    cur.execute("UPDATE maclasse SET accessLock=? WHERE folder=?", (
        bool(int(request.args.get("lock"))),
        userData[0][0]
    ))
    return redirect("/maclasse/index")



# ----- Launch ----- #
if __name__ == "__main__":
    try:
        app.logger.info("server start")
        print(
            "# ----- # ----- #",
            build_tree(CONFIG["directory tree"]),
            f"debug: {DEBUG}",
            f"os: {OS}",
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
