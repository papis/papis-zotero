all: help

help: 								## Show this help
	@echo -e "Specify a command. The choices are:\n"
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[0;36m%-18s\033[m %s\n", $$1, $$2}'
	@echo ""
.PHONY: help

tags:								## Generate ctags for main codebase
	ctags -f tags \
		--recurse=yes \
		--tag-relative=yes \
		--fields=+l \
		--kinds-python=-i \
		--language-force=python \
		papis_zotero
.PHONY: tags

ruff:								## Run ruff checks
	ruff check papis_zotero tests
.PHONY: ruff

mypy:								## Run (strict) mypy checks
	python -m mypy papis_zotero tests
.PHONY: mypy

pytest:								## Run pytest test and doctests
	python -m pytest -rswx -v -s tests
.PHONY: pytest

ci-install-build-system:
	python -m pip install --upgrade pip hatchling wheel build
.PHONY: ci-install-build-system

ci-install: ci-install-build-system	## Run pip and install dependencies on CI
	python -m pip install -e '.[develop]'
.PHONY: ci-install
