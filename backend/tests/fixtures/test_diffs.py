"""Test diff fixtures for prompt tuning and integration testing."""

# 1. SQL Injection — string concatenation in a Flask/SQLAlchemy route
SQL_INJECTION_DIFF = """\
diff --git a/app/routes/users.py b/app/routes/users.py
--- a/app/routes/users.py
+++ b/app/routes/users.py
@@ -10,6 +10,14 @@
 from flask import Flask, request, jsonify
 from database import db
 
+@app.route("/users/search")
+def search_users():
+    name = request.args.get("name")
+    query = f"SELECT * FROM users WHERE name = '{name}'"
+    results = db.engine.execute(query)
+    return jsonify([dict(r) for r in results])
+
+
 @app.route("/health")
 def health():
     return "ok"
"""

# 2. XSS — reflected cross-site scripting in a template / response
XSS_DIFF = """\
diff --git a/app/views/profile.py b/app/views/profile.py
--- a/app/views/profile.py
+++ b/app/views/profile.py
@@ -5,6 +5,15 @@
 from flask import Flask, request, make_response
 
+@app.route("/greet")
+def greet():
+    username = request.args.get("username", "guest")
+    html = f"<h1>Welcome, {username}!</h1>"
+    return make_response(html)
+
+@app.route("/comment")
+def render_comment():
+    comment = request.form.get("body")
+    return f"<div class='comment'>{comment}</div>"
"""

# 3. Insecure deserialization + path traversal
DESER_PATH_TRAVERSAL_DIFF = """\
diff --git a/app/services/importer.py b/app/services/importer.py
--- a/app/services/importer.py
+++ b/app/services/importer.py
@@ -1,5 +1,18 @@
 import os
 import pickle
+import yaml
+from flask import request, send_file
+
+@app.route("/import", methods=["POST"])
+def import_data():
+    raw = request.get_data()
+    data = pickle.loads(raw)
+    return process(data)
+
+@app.route("/download")
+def download_file():
+    filename = request.args.get("file")
+    path = os.path.join("/var/data", filename)
+    return send_file(path)
"""

# 4. Clean diff — no security issues expected
CLEAN_DIFF = """\
diff --git a/app/utils/formatting.py b/app/utils/formatting.py
--- a/app/utils/formatting.py
+++ b/app/utils/formatting.py
@@ -1,4 +1,12 @@
 import re
+from datetime import datetime, timezone
+
+
+def format_timestamp(dt: datetime) -> str:
+    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+
+
+def slugify(text: str) -> str:
+    text = text.lower().strip()
+    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")
"""
