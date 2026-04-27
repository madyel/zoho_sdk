# Minimal makefile for Sphinx docs

SPHINXOPTS  ?=
SPHINXBUILD ?= sphinx-build
SOURCEDIR   = .
BUILDDIR    = _build

.PHONY: help clean html html-it html-en gettext

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	rm -rf $(BUILDDIR)

html:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html/en" -D language=en $(SPHINXOPTS)
	@echo "English docs: $(BUILDDIR)/html/en/index.html"

html-it:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html/it" -D language=it $(SPHINXOPTS)
	@echo "Italian docs: $(BUILDDIR)/html/it/index.html"

html-en: html

gettext:
	$(SPHINXBUILD) -b gettext "$(SOURCEDIR)" "$(BUILDDIR)/gettext" $(SPHINXOPTS)
	@echo "Run: sphinx-intl update -p $(BUILDDIR)/gettext -l it"
