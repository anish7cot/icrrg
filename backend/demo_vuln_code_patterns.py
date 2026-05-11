"""
Vulnerable web application patterns — FOR TESTING/DEMO ONLY.
Contains OWASP Top 10 code-level vulnerabilities that Veracode-style
static analysis and the ICRRG LLM review engine should detect.

CWE Coverage:
  - CWE-89:  SQL Injection
  - CWE-79:  Cross-Site Scripting (XSS)
  - CWE-78:  OS Command Injection
  - CWE-22:  Path Traversal
  - CWE-502: Insecure Deserialization
  - CWE-327: Broken Cryptography (MD5/SHA1 for passwords)
  - CWE-611: XML External Entity (XXE)
  - CWE-918: Server-Side Request Forgery (SSRF)
  - CWE-295: Improper Certificate Validation
  - CWE-676: Use of Potentially Dangerous Functions (eval)
  - CWE-94:  Code Injection
  - CWE-614: Missing Secure Cookie Flag
  - CWE-532: Information Exposure Through Log Files
"""

import hashlib
import logging
import os
import pickle
import subprocess
import sqlite3
import xml.etree.ElementTree as ET

import requests
from flask import Flask, request, make_response, redirect, render_template_string

app = Flask(__name__)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# CWE-89: SQL Injection
# ═══════════════════════════════════════════════════════════════════════
@app.route("/user")
def get_user():
    username = request.args.get("username")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return str(cursor.fetchone())


@app.route("/search")
def search_products():
    query = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + query + "%'")
    return str(cursor.fetchall())


# ═══════════════════════════════════════════════════════════════════════
# CWE-79: Cross-Site Scripting (Reflected XSS)
# ═══════════════════════════════════════════════════════════════════════
@app.route("/greet")
def greet():
    name = request.args.get("name", "")
    return f"<h1>Hello, {name}!</h1>"


@app.route("/profile")
def profile():
    bio = request.args.get("bio", "")
    template = f"<div class='bio'>{bio}</div>"
    return render_template_string(template)


# ═══════════════════════════════════════════════════════════════════════
# CWE-78: OS Command Injection
# ═══════════════════════════════════════════════════════════════════════
@app.route("/ping")
def ping():
    host = request.args.get("host")
    output = os.popen(f"ping -c 3 {host}").read()
    return f"<pre>{output}</pre>"


@app.route("/lookup")
def dns_lookup():
    domain = request.args.get("domain")
    result = subprocess.run(
        f"nslookup {domain}", shell=True, capture_output=True, text=True
    )
    return result.stdout


# ═══════════════════════════════════════════════════════════════════════
# CWE-22: Path Traversal / Directory Traversal
# ═══════════════════════════════════════════════════════════════════════
@app.route("/download")
def download_file():
    filename = request.args.get("file")
    filepath = os.path.join("/var/app/uploads", filename)
    with open(filepath, "r") as f:
        return f.read()


@app.route("/logs")
def view_log():
    log_name = request.args.get("name")
    content = open(f"/var/log/{log_name}").read()
    return f"<pre>{content}</pre>"


# ═══════════════════════════════════════════════════════════════════════
# CWE-502: Insecure Deserialization
# ═══════════════════════════════════════════════════════════════════════
@app.route("/import", methods=["POST"])
def import_data():
    data = request.get_data()
    obj = pickle.loads(data)
    return f"Imported: {obj}"


@app.route("/session")
def load_session():
    cookie = request.cookies.get("session_data")
    if cookie:
        import base64
        session_obj = pickle.loads(base64.b64decode(cookie))
        return f"Welcome back, {session_obj['username']}"
    return "No session"


# ═══════════════════════════════════════════════════════════════════════
# CWE-327: Use of Broken Crypto (MD5/SHA1 for passwords)
# ═══════════════════════════════════════════════════════════════════════
def hash_password_md5(password):
    return hashlib.md5(password.encode()).hexdigest()


def hash_password_sha1(password):
    return hashlib.sha1(password.encode()).hexdigest()


def verify_user(username, password):
    stored_hash = get_stored_hash(username)
    return stored_hash == hashlib.md5(password.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════
# CWE-611: XML External Entity (XXE)
# ═══════════════════════════════════════════════════════════════════════
@app.route("/parse-xml", methods=["POST"])
def parse_xml():
    xml_data = request.get_data()
    tree = ET.fromstring(xml_data)
    return ET.tostring(tree, encoding="unicode")


@app.route("/import-config", methods=["POST"])
def import_config():
    from lxml import etree
    xml_content = request.get_data()
    parser = etree.XMLParser(resolve_entities=True)
    doc = etree.fromstring(xml_content, parser)
    return etree.tostring(doc, encoding="unicode")


# ═══════════════════════════════════════════════════════════════════════
# CWE-918: Server-Side Request Forgery (SSRF)
# ═══════════════════════════════════════════════════════════════════════
@app.route("/fetch")
def fetch_url():
    url = request.args.get("url")
    response = requests.get(url)
    return response.text


@app.route("/webhook")
def webhook_proxy():
    target = request.args.get("target")
    data = request.get_json()
    resp = requests.post(target, json=data)
    return resp.text


# ═══════════════════════════════════════════════════════════════════════
# CWE-295: Improper Certificate Validation
# ═══════════════════════════════════════════════════════════════════════
def call_external_api(endpoint, payload):
    return requests.post(
        f"https://api.partner.com/{endpoint}",
        json=payload,
        verify=False,
    )


# ═══════════════════════════════════════════════════════════════════════
# CWE-676 / CWE-94: Dangerous eval() and exec()
# ═══════════════════════════════════════════════════════════════════════
@app.route("/calc")
def calculator():
    expression = request.args.get("expr")
    result = eval(expression)
    return f"Result: {result}"


@app.route("/run-code", methods=["POST"])
def run_code():
    code = request.form.get("code")
    exec(code)
    return "Executed"


# ═══════════════════════════════════════════════════════════════════════
# CWE-614: Missing Secure Cookie Flags
# ═══════════════════════════════════════════════════════════════════════
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    if authenticate(username, password):
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("auth_token", generate_token(username))
        resp.set_cookie("user_role", "admin", httponly=False)
        return resp
    return "Invalid credentials", 401


# ═══════════════════════════════════════════════════════════════════════
# CWE-532: Sensitive Data Logged
# ═══════════════════════════════════════════════════════════════════════
@app.route("/api/login", methods=["POST"])
def api_login():
    creds = request.get_json()
    logger.info(f"Login attempt: username={creds['username']}, password={creds['password']}")
    if authenticate(creds["username"], creds["password"]):
        token = generate_token(creds["username"])
        logger.info(f"Token generated: {token}")
        return {"token": token}
    logger.warning(f"Failed login for {creds['username']} with password {creds['password']}")
    return {"error": "unauthorized"}, 401


# ═══════════════════════════════════════════════════════════════════════
# CWE-1004: Missing HttpOnly Flag + CWE-1275: Sensitive Cookie Without
# 'Secure' Flag
# ═══════════════════════════════════════════════════════════════════════
@app.route("/set-prefs")
def set_preferences():
    session_id = request.cookies.get("JSESSIONID")
    resp = make_response("OK")
    resp.set_cookie("session", session_id, secure=False, httponly=False, samesite="None")
    return resp


# ═══════════════════════════════════════════════════════════════════════
# CWE-250 / CWE-732: Overly Permissive File Operations
# ═══════════════════════════════════════════════════════════════════════
def save_upload(file_content, filename):
    path = f"/var/app/uploads/{filename}"
    with open(path, "wb") as f:
        f.write(file_content)
    os.chmod(path, 0o777)


# ═══════════════════════════════════════════════════════════════════════
# Helper stubs (not real — just so the file parses)
# ═══════════════════════════════════════════════════════════════════════
def authenticate(username, password):
    return True

def generate_token(username):
    return hashlib.md5(username.encode()).hexdigest()

def get_stored_hash(username):
    return ""
"""
Vulnerable web application patterns — FOR TESTING/DEMO ONLY.
Contains OWASP Top 10 code-level vulnerabilities that Veracode-style
static analysis and the ICRRG LLM review engine should detect.

CWE Coverage:
  - CWE-89:  SQL Injection
  - CWE-79:  Cross-Site Scripting (XSS)
  - CWE-78:  OS Command Injection
  - CWE-22:  Path Traversal
  - CWE-502: Insecure Deserialization
  - CWE-327: Broken Cryptography (MD5/SHA1 for passwords)
  - CWE-611: XML External Entity (XXE)
  - CWE-918: Server-Side Request Forgery (SSRF)
  - CWE-295: Improper Certificate Validation
  - CWE-676: Use of Potentially Dangerous Functions (eval)
  - CWE-94:  Code Injection
  - CWE-614: Missing Secure Cookie Flag
  - CWE-532: Information Exposure Through Log Files
"""

import hashlib
import logging
import os
import pickle
import subprocess
import sqlite3
import xml.etree.ElementTree as ET

import requests
from flask import Flask, request, make_response, redirect, render_template_string

app = Flask(__name__)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# CWE-89: SQL Injection
# ═══════════════════════════════════════════════════════════════════════
@app.route("/user")
def get_user():
    username = request.args.get("username")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return str(cursor.fetchone())


@app.route("/search")
def search_products():
    query = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + query + "%'")
    return str(cursor.fetchall())


# ═══════════════════════════════════════════════════════════════════════
# CWE-79: Cross-Site Scripting (Reflected XSS)
# ═══════════════════════════════════════════════════════════════════════
@app.route("/greet")
def greet():
    name = request.args.get("name", "")
    return f"<h1>Hello, {name}!</h1>"


@app.route("/profile")
def profile():
    bio = request.args.get("bio", "")
    template = f"<div class='bio'>{bio}</div>"
    return render_template_string(template)


# ═══════════════════════════════════════════════════════════════════════
# CWE-78: OS Command Injection
# ═══════════════════════════════════════════════════════════════════════
@app.route("/ping")
def ping():
    host = request.args.get("host")
    output = os.popen(f"ping -c 3 {host}").read()
    return f"<pre>{output}</pre>"


@app.route("/lookup")
def dns_lookup():
    domain = request.args.get("domain")
    result = subprocess.run(
        f"nslookup {domain}", shell=True, capture_output=True, text=True
    )
    return result.stdout


# ═══════════════════════════════════════════════════════════════════════
# CWE-22: Path Traversal / Directory Traversal
# ═══════════════════════════════════════════════════════════════════════
@app.route("/download")
def download_file():
    filename = request.args.get("file")
    filepath = os.path.join("/var/app/uploads", filename)
    with open(filepath, "r") as f:
        return f.read()


@app.route("/logs")
def view_log():
    log_name = request.args.get("name")
    content = open(f"/var/log/{log_name}").read()
    return f"<pre>{content}</pre>"


# ═══════════════════════════════════════════════════════════════════════
# CWE-502: Insecure Deserialization
# ═══════════════════════════════════════════════════════════════════════
@app.route("/import", methods=["POST"])
def import_data():
    data = request.get_data()
    obj = pickle.loads(data)
    return f"Imported: {obj}"


@app.route("/session")
def load_session():
    cookie = request.cookies.get("session_data")
    if cookie:
        import base64
        session_obj = pickle.loads(base64.b64decode(cookie))
        return f"Welcome back, {session_obj['username']}"
    return "No session"


# ═══════════════════════════════════════════════════════════════════════
# CWE-327: Use of Broken Crypto (MD5/SHA1 for passwords)
# ═══════════════════════════════════════════════════════════════════════
def hash_password_md5(password):
    return hashlib.md5(password.encode()).hexdigest()


def hash_password_sha1(password):
    return hashlib.sha1(password.encode()).hexdigest()


def verify_user(username, password):
    stored_hash = get_stored_hash(username)
    return stored_hash == hashlib.md5(password.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════
# CWE-611: XML External Entity (XXE)
# ═══════════════════════════════════════════════════════════════════════
@app.route("/parse-xml", methods=["POST"])
def parse_xml():
    xml_data = request.get_data()
    tree = ET.fromstring(xml_data)
    return ET.tostring(tree, encoding="unicode")


@app.route("/import-config", methods=["POST"])
def import_config():
    from lxml import etree
    xml_content = request.get_data()
    parser = etree.XMLParser(resolve_entities=True)
    doc = etree.fromstring(xml_content, parser)
    return etree.tostring(doc, encoding="unicode")


# ═══════════════════════════════════════════════════════════════════════
# CWE-918: Server-Side Request Forgery (SSRF)
# ═══════════════════════════════════════════════════════════════════════
@app.route("/fetch")
def fetch_url():
    url = request.args.get("url")
    response = requests.get(url)
    return response.text


@app.route("/webhook")
def webhook_proxy():
    target = request.args.get("target")
    data = request.get_json()
    resp = requests.post(target, json=data)
    return resp.text


# ═══════════════════════════════════════════════════════════════════════
# CWE-295: Improper Certificate Validation
# ═══════════════════════════════════════════════════════════════════════
def call_external_api(endpoint, payload):
    return requests.post(
        f"https://api.partner.com/{endpoint}",
        json=payload,
        verify=False,
    )


# ═══════════════════════════════════════════════════════════════════════
# CWE-676 / CWE-94: Dangerous eval() and exec()
# ═══════════════════════════════════════════════════════════════════════
@app.route("/calc")
def calculator():
    expression = request.args.get("expr")
    result = eval(expression)
    return f"Result: {result}"


@app.route("/run-code", methods=["POST"])
def run_code():
    code = request.form.get("code")
    exec(code)
    return "Executed"


# ═══════════════════════════════════════════════════════════════════════
# CWE-614: Missing Secure Cookie Flags
# ═══════════════════════════════════════════════════════════════════════
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    if authenticate(username, password):
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("auth_token", generate_token(username))
        resp.set_cookie("user_role", "admin", httponly=False)
        return resp
    return "Invalid credentials", 401


# ═══════════════════════════════════════════════════════════════════════
# CWE-532: Sensitive Data Logged
# ═══════════════════════════════════════════════════════════════════════
@app.route("/api/login", methods=["POST"])
def api_login():
    creds = request.get_json()
    logger.info(f"Login attempt: username={creds['username']}, password={creds['password']}")
    if authenticate(creds["username"], creds["password"]):
        token = generate_token(creds["username"])
        logger.info(f"Token generated: {token}")
        return {"token": token}
    logger.warning(f"Failed login for {creds['username']} with password {creds['password']}")
    return {"error": "unauthorized"}, 401


# ═══════════════════════════════════════════════════════════════════════
# CWE-1004: Missing HttpOnly Flag + CWE-1275: Sensitive Cookie Without
# 'Secure' Flag
# ═══════════════════════════════════════════════════════════════════════
@app.route("/set-prefs")
def set_preferences():
    session_id = request.cookies.get("JSESSIONID")
    resp = make_response("OK")
    resp.set_cookie("session", session_id, secure=False, httponly=False, samesite="None")
    return resp


# ═══════════════════════════════════════════════════════════════════════
# CWE-250 / CWE-732: Overly Permissive File Operations
# ═══════════════════════════════════════════════════════════════════════
def save_upload(file_content, filename):
    path = f"/var/app/uploads/{filename}"
    with open(path, "wb") as f:
        f.write(file_content)
    os.chmod(path, 0o777)


# ═══════════════════════════════════════════════════════════════════════
# Helper stubs (not real — just so the file parses)
# ═══════════════════════════════════════════════════════════════════════
def authenticate(username, password):
    return True

def generate_token(username):
    return hashlib.md5(username.encode()).hexdigest()

def get_stored_hash(username):
    return ""
