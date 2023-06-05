# ----- Lib ----- #
from flask import Flask
from subprocess import getoutput
from yaml import safe_load
from mariadb import connect
from os import (
    mkdir,
    listdir
)
from os.path import isdir
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



# ----- Set Up ----- #
# os detection
OS = platform

# absolute path of file
if OS == "win32":
    PATH = '\\'.join(__file__.split('\\')[:-1])
else:
    PATH = '/'.join(__file__.split('/')[:-1])

# out is a adaptive platfom path
check_path = lambda path: path.replace('/', '\\') if OS == "win32" else path

# safe load yaml
with open(check_path(f"{PATH}/config.yaml"), 'r') as config_file:
    CONFIG = safe_load(config_file)

# load config from yaml
__version__ = CONFIG["version"]
DEBUG = CONFIG["debug"]

# prod only avaible on linux
if DEBUG:
    IPADDRESS = CONFIG[f"debug {OS}"]["ip address"]
    PORT = CONFIG[f"debug {OS}"]["https port"]
    KEYFILE = CONFIG[f"debug {OS}"]["key file"]
    CERTFILE = CONFIG[f"debug {OS}"]["cert file"]
else:
    IPADDRESS = CONFIG[f"prod {OS}"]["ip address"]
    PORT = CONFIG[f"prod {OS}"]["https port"]
    KEYFILE = CONFIG[f"prod {OS}"]["key file"]
    CERTFILE = CONFIG[f"prod {OS}"]["cert file"]

# load mail content
with open(check_path(f"{PATH}/templates/mail.html"), 'r') as f:
    HTMLMAIL = f.read()

# dict var for maclasse register timeout
maclasseRegisterTmpData = {}

# var for located potential error
error500Handle = None



# ----- Def ----- #
def build_tree(tree: dict) -> None:
    """build directory tree from config spec"""
    mainDirList = [] #[f for f in listdir(check_path(PATH)) if isdir(check_path(f"{PATH}/{f}"))]
    for elem in listdir(check_path(PATH)):
        if isdir(check_path(f"{PATH}/{elem}")):
            mainDirList.append(elem)
    for mainDir in tree:
        if not mainDir in mainDirList:
            mkdir(check_path(f"{PATH}/{mainDir}"))
        subDirList = [] #[f for f in listdir(check_path(f"{PATH}/{mainDir}")) if isdir(check_path(f"{PATH}/{mainDir}/{f}"))]
        for elem in listdir(check_path(f"{PATH}/{mainDir}")):
            if isdir(check_path(f"{PATH}/{mainDir}/{elem}")):
                subDirList.append(elem)
        if tree[mainDir]:
            for subDir in tree[mainDir]:
                if not subDir in subDirList:
                    mkdir(check_path(f"{PATH}/{mainDir}/{subDir}"))
    return tree

def send_mail(app: Flask, inTextVar: dict, htmlContent: str, subject: str, mailFrom: str, mailTo: str) -> None:
    """send mail with postfix"""
    app.logger.info(inTextVar["mailCode"])
    if OS == "linux":
        for elem in inTextVar:
            htmlContent.replace("{{ " + elem + " }}", inTextVar[elem])
        getoutput(f"""printf "{htmlContent}" | mail --content-type=text/html -s "{subject}" -a From:{mailFrom} {mailTo}""")

def check_maclasseRegisterTmpData(app: Flask) -> None:
    """check timeout for maclasse register"""
    app.logger.info(f"tread {current_thread().name} start")
    while True:
        dataListToDel = []
        for data in maclasseRegisterTmpData:
            if maclasseRegisterTmpData[data]["date"] + timedelta(minutes=10) < datetime.now():
                app.logger.info(f"del {data}: {maclasseRegisterTmpData[data]}")
                dataListToDel.append(data)
        for data in dataListToDel:
            del maclasseRegisterTmpData[data]
        sleep(1)

def add_versions(v1: str, v2: str) -> str:
    """file version incremetation"""
    if not v1:
        v1 = "0.0.0"
    v1List = v1.split('.')
    out = ''
    if v2:
        v2List = v2.split('.')
        if len(v2List) == 3:
            v3List = []
            v3List.append(int(v1List[0]) + int(v2List[0]))
            v3List.append((int(v1List[1]) + int(v2List[1])) if v3List[0] == 0 else int(v2List[1]))
            v3List.append((int(v1List[2]) + int(v2List[2])) if v3List[0] == 0 and v3List[1] == 0 else int(v2List[2]))
            for i in v3List:
                out += str(i) + '.'
            return out[:-1]
    v1List[2] = int(v1List[2]) + 1
    for i in v1List:
        out += str(i) + '.'
    return out[:-1]


# thread object for maclasse register timeout
maclasseRegisterTmpDataThread = Thread(target=check_maclasseRegisterTmpData, daemon=True)



# ----- SQL ----- #
conn = connect(
   user=CONFIG["database"]["user"],
   password=CONFIG["database"]["password"],
   host=CONFIG["database"]["host"],
   autocommit=True
)
cur = conn.cursor()
cur.execute(f"""CREATE DATABASE IF NOT EXISTS {CONFIG["database"]["name"]}""")
conn = connect(
    user=CONFIG["database"]["user"],
    password=CONFIG["database"]["password"],
    host=CONFIG["database"]["host"],
    database=CONFIG["database"]["name"],
    autocommit=True
)
cur = conn.cursor()
cur.execute("SET SESSION interactive_timeout=31536000")
cur.execute("SET SESSION wait_timeout=31536000")
cur.execute(
    """CREATE TABLE IF NOT EXISTS maclasse (
        folder INT NOT NULL AUTO_INCREMENT PRIMARY KEY UNIQUE KEY,
        token TEXT,
        id TEXT,
        pw TEXT,
        profPw TEXT,
        accessLock INT,
        title TEXT,
        bgPic TEXT,
        color TEXT
    )"""
)
cur.execute(
    """CREATE TABLE IF NOT EXISTS maclasseShareDict (
        picId TEXT,
        path TEXT
    )"""
)
cur.execute(
    """CREATE TABLE IF NOT EXISTS depot (
        tokenGET TEXT,
        tokenPOST TEXT
    )"""
)