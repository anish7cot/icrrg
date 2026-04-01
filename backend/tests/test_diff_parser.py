"""Tests for the unified diff parser."""

from app.git.diff_parser import parse_unified_diff


# ---------------------------------------------------------------------------
# Sample diffs
# ---------------------------------------------------------------------------

SINGLE_FILE_DIFF = """\
diff --git a/src/utils.py b/src/utils.py
index 1234567..abcdefg 100644
--- a/src/utils.py
+++ b/src/utils.py
@@ -1,4 +1,5 @@
 import os
+import sys
 import json
-import yaml
 
+# added comment
"""

MULTI_FILE_DIFF = """\
diff --git a/app/main.py b/app/main.py
index aaa..bbb 100644
--- a/app/main.py
+++ b/app/main.py
@@ -10,3 +10,4 @@
 app = FastAPI()
 
+# new endpoint
 @app.get("/health")
diff --git a/app/config.py b/app/config.py
index ccc..ddd 100644
--- a/app/config.py
+++ b/app/config.py
@@ -1,2 +1,3 @@
 DEBUG = True
+SECRET = "hunter2"
 PORT = 8000
"""

NEW_FILE_DIFF = """\
diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+line one
+line two
+line three
"""

BINARY_FILE_DIFF = """\
diff --git a/image.png b/image.png
new file mode 100644
index 0000000..abcdef1
Binary files /dev/null and b/image.png differ
diff --git a/readme.md b/readme.md
index 111..222 100644
--- a/readme.md
+++ b/readme.md
@@ -1,2 +1,3 @@
 # Title
+New paragraph
 End
"""

RENAMED_FILE_DIFF = """\
diff --git a/old_name.py b/new_name.py
similarity index 90%
rename from old_name.py
rename to new_name.py
index aaa..bbb 100644
--- a/old_name.py
+++ b/new_name.py
@@ -1,3 +1,3 @@
 def hello():
-    print("old")
+    print("new")
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_single_file_diff():
    result = parse_unified_diff(SINGLE_FILE_DIFF)

    assert len(result.files) == 1
    f = result.files[0]
    assert f.old_path == "src/utils.py"
    assert f.new_path == "src/utils.py"
    assert f.is_binary is False

    added = f.added_lines
    removed = f.removed_lines
    assert len(added) == 2  # "import sys" and "# added comment"
    assert len(removed) == 1  # "import yaml"

    # Verify line numbers (1-indexed, new-file numbering for adds)
    assert added[0].line_number == 2
    assert added[0].content == "import sys"
    assert added[1].content == "# added comment"

    # Removed line uses old-file numbering
    assert removed[0].content == "import yaml"


def test_multi_file_diff():
    result = parse_unified_diff(MULTI_FILE_DIFF)

    assert len(result.files) == 2
    assert result.files[0].new_path == "app/main.py"
    assert result.files[1].new_path == "app/config.py"

    # First file: 1 addition
    assert len(result.files[0].added_lines) == 1
    assert result.files[0].added_lines[0].content == "# new endpoint"

    # Second file: 1 addition
    assert len(result.files[1].added_lines) == 1
    assert result.files[1].added_lines[0].content == 'SECRET = "hunter2"'

    # Aggregate counts
    assert result.total_additions == 2
    assert result.total_deletions == 0


def test_new_file_diff():
    result = parse_unified_diff(NEW_FILE_DIFF)

    assert len(result.files) == 1
    f = result.files[0]
    assert f.old_path is None  # /dev/null → None
    assert f.new_path == "new_file.py"
    assert len(f.added_lines) == 3
    assert f.added_lines[0].line_number == 1
    assert f.added_lines[1].line_number == 2
    assert f.added_lines[2].line_number == 3


def test_binary_file_skipped():
    result = parse_unified_diff(BINARY_FILE_DIFF)

    assert len(result.files) == 2
    # Binary file recorded but has no parsed lines
    assert result.files[0].is_binary is True
    assert len(result.files[0].lines) == 0

    # Text file after binary is still parsed correctly
    assert result.files[1].new_path == "readme.md"
    assert len(result.files[1].added_lines) == 1
    assert result.files[1].added_lines[0].content == "New paragraph"


def test_renamed_file():
    result = parse_unified_diff(RENAMED_FILE_DIFF)

    assert len(result.files) == 1
    f = result.files[0]
    assert f.old_path == "old_name.py"
    assert f.new_path == "new_name.py"
    assert len(f.added_lines) == 1
    assert len(f.removed_lines) == 1
    assert f.added_lines[0].content == '    print("new")'
    assert f.removed_lines[0].content == '    print("old")'


def test_empty_diff():
    result = parse_unified_diff("")
    assert len(result.files) == 0
    assert result.total_additions == 0
    assert result.total_deletions == 0
