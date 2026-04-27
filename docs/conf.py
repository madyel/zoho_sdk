"""Sphinx configuration for zoho-people-sdk documentation."""
from __future__ import annotations

import sys
from pathlib import Path

# Make sure the src package is importable
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------
project   = "zoho-people-sdk"
author    = "madyel83"
copyright = "2026, madyel83"
release   = "0.1.0"
version   = "0.1"

# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",          # API docs from docstrings
    "sphinx.ext.autosummary",      # summary tables
    "sphinx.ext.napoleon",         # NumPy / Google docstrings
    "sphinx.ext.viewcode",         # [source] links
    "sphinx.ext.intersphinx",      # cross-ref to Python / requests docs
    "sphinx_copybutton",           # copy button on code blocks
    "myst_parser",                 # Markdown support
]

# ---------------------------------------------------------------------------
# Source / output
# ---------------------------------------------------------------------------
source_suffix  = {".rst": "restructuredtext", ".md": "markdown"}
master_doc     = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]
html_static_path = ["_static"]

# ---------------------------------------------------------------------------
# i18n / multilanguage
# ---------------------------------------------------------------------------
language = "en"           # default language
locale_dirs   = ["locale"]
gettext_compact = False   # one .pot file per .rst file (easier to translate)
gettext_uuid  = False

# ---------------------------------------------------------------------------
# HTML theme – Furo (clean, modern, dark-mode)
# ---------------------------------------------------------------------------
html_theme = "furo"
html_title = "zoho-people-sdk"
html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "source_repository": "https://github.com/madyel83/zoho-people-sdk/",
    "source_branch": "main",
    "source_directory": "docs/",
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/madyel83/zoho-people-sdk",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0"
                    viewBox="0 0 16 16" height="1em" width="1em">
                  <path fill-rule="evenodd"
                    d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
                       0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
                       -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
                       .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15
                       -.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27
                       .68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12
                       .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48
                       0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8
                       c0-4.42-3.58-8-8-8z"/>
                </svg>
            """,
            "class": "",
        },
    ],
}

# ---------------------------------------------------------------------------
# Autodoc
# ---------------------------------------------------------------------------
autodoc_default_options = {
    "members":          True,
    "undoc-members":    False,
    "show-inheritance": True,
    "member-order":     "bysource",
}
autodoc_typehints        = "description"
autodoc_typehints_format = "short"
napoleon_google_docstring = False
napoleon_numpy_docstring  = True
napoleon_use_param        = True
napoleon_use_rtype        = True

autosummary_generate = True

# ---------------------------------------------------------------------------
# Intersphinx
# ---------------------------------------------------------------------------
intersphinx_mapping = {
    "python":   ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
}
