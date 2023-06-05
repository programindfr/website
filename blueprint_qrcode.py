# ----- Lib ----- #
from flask import (
    Blueprint,
    request,
    render_template,
    send_from_directory
)
from datetime import datetime
from werkzeug.utils import secure_filename
from qrcode import make
from web_main_setup import (
    check_path,
    PATH,
    CONFIG,
    __version__
)



# ----- Set Up ----- #
blueprintQrcode = Blueprint("blueprintQrcode", __name__)
blueprintQrcode.logger.setLevel(20)



# qrcode
@blueprintQrcode.route("/qrcode", methods=["GET"])
def qrcode_GET():
	return render_template(
        "qrcodeGET.html",
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

@blueprintQrcode.route("/qrcode", methods=["POST"])
def qrcode_POST():
    ID = secure_filename(str(datetime.now()))
    make(request.form["data"]).save(check_path(f"{PATH}/qrcode/{ID}.png"))
    return render_template(
        "qrcodePOST.html",
        id=ID,
        websiteName=CONFIG["website name"],
        version=__version__,
        contactMail=CONFIG["mail"]["contact"]
    )

@blueprintQrcode.route("/qrcode/dl/<string:ID>", methods=["GET"])
def qrcode_dl(ID):
	return send_from_directory(
        check_path(f"{PATH}/qrcode"),
        f"{ID}.png"
    )