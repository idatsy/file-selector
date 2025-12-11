"""Minimal tests for file_selector core functions."""

import os
import tempfile

from file_selector.__main__ import get_language_for_file, build_file_tree, IGNORED_DIRS


class TestGetLanguageForFile:
    """Test language detection by file extension."""

    def test_common_extensions(self):
        assert get_language_for_file("main.py") == "python"
        assert get_language_for_file("app.js") == "javascript"
        assert get_language_for_file("App.tsx") == "typescript"
        assert get_language_for_file("style.css") == "css"
        assert get_language_for_file("config.json") == "json"
        assert get_language_for_file("README.md") == "markdown"

    def test_unknown_extension(self):
        assert get_language_for_file("file.xyz") == ""
        assert get_language_for_file("no_extension") == ""

    def test_case_insensitive(self):
        assert get_language_for_file("FILE.PY") == "python"
        assert get_language_for_file("App.JSX") == "javascript"


class TestBuildFileTree:
    """Test file tree building with ignore patterns."""

    def test_ignores_common_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a regular file and some ignored directories
            open(os.path.join(tmpdir, "main.py"), "w").close()
            os.makedirs(os.path.join(tmpdir, "src"))
            open(os.path.join(tmpdir, "src", "app.py"), "w").close()
            for ignored in [".git", "node_modules", "__pycache__"]:
                os.makedirs(os.path.join(tmpdir, ignored))
                open(os.path.join(tmpdir, ignored, "file.txt"), "w").close()

            tree = build_file_tree(tmpdir)
            paths = [entry[0] for entry in tree]

            assert "main.py" in paths
            assert "src" in paths
            for ignored in [".git", "node_modules", "__pycache__"]:
                assert ignored not in paths
