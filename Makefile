PROJECT = forgefrenzy
SOURCES = $(wildcard src/$(PROJECT)/*.py)
VERSION = $(shell cat VERSION)

PYTHON3 = python3
PIP3 = pip3
PYTHON_PATH = $(shell dirname $(shell which python3))
PYTHON_VERSION = 3.10
TERRAFORM_BIN = $(shell which terraform)
TERRAFORM = $(shell which terraform) -chdir=terraform/

VENV_PATH = .venv
VENV_BIN = $(VENV_PATH)/bin
ACTIVATE = $(VENV_BIN)/activate

.PHONY: all
all: pip deploy
localdev: hooks test build
pip: hooks test VERSION build upload install
deploy: hooks test build lambda terraform

lambda:
	#@do something


$(TERRAFORM_BIN):
	@brew install terraform

terraform/.terraform: $(TERRAFORM_BIN)
terraform/.terraform:
	$(TERRAFORM) init


.PHONY: terraform
terraform: terraform/.terraform
terraform: CONFIG ?= terraform/vars.tf
terraform: ENVIRONMENT ?= staging
terraform:
	if ! $(TERRAFORM) workspace list 2>&1 | grep -qi "$(ENVIRONMENT)"; then \
    	$(TERRAFORM) workspace new "$(ENVIRONMENT)"; \
    fi
	$(TERRAFORM) workspace select "$(ENVIRONMENT)"
	$(TERRAFORM) get
	$(TERRAFORM) plan -var-file=$(CONFIG)
	#@$(TERRAFORM) apply -var-file=$(CONFIG)



.PHONY: venv
venv: $(VENV_PATH)
	@rm -rf $(VENV_PATH)
	@$(MAKE) $(VENV_PATH)


.PHONY: bump
bump:
	 @BUMP=patch $(MAKE) -B VERSION
	
.PHONY: major 
major:
	@BUMP=major $(MAKE) -B VERSION
	
.PHONY: minor
minor:
	 @BUMP=minor $(MAKE) -B VERSION
	
# Format and test targets
.PHONY: test
test: $(ACTIVATE)
test: format
test:
	@. $(ACTIVATE) && PYTHONPATH=src $(PYTHON3) -m $(PROJECT) --test
	@. $(ACTIVATE) && PYTHONPATH=src $(PYTHON3) -m $(PROJECT).blueplate.special --test

.PHONY: format
format: $(VENV_BIN)/black
	@$(VENV_BIN)/black src/

# Build targets 
.PHONY: clean
clean:
	@rm -rf dist/

.PHONY: build
build: VERSION
build: dist/forgefrenzy-$(VERSION).tar.gz

.PHONY: run
run:
	@printf "$(PYTHON3) -m $(PROJECT) "
	@read ARGS
	@echo "Args: ${ARGS}"
	@. $(ACTIVATE) && PYTHONPATH=src $(PYTHON3) -m $(PROJECT) -vv $(ARGS)

$(SOURCES):
	echo "Sources have changed..."

dist/$(PROJECT)-$(VERSION)-py3-none-any.whl: dist/$(PROJECT)-$(VERSION).tar.gz

dist/forgefrenzy-$(VERSION).tar.gz: $(SOURCES)
	@. $(ACTIVATE) && $(PYTHON3) -m build

.PHONY: VERSION
VERSION: CURRENT_VERSION := $(shell cat VERSION)
VERSION: $(VENV_BIN)/pysemver
VERSION: BUMP ?= patch
VERSION:
	@pysemver bump $(BUMP) $(CURRENT_VERSION) > VERSION
	@echo "version = \"`cat VERSION`\"" > src/$(PROJECT)/version.py
	@echo "Version bumped: $(CURRENT_VERSION) -> `cat VERSION`"
	@$(MAKE) clean

# venv tools
$(VENV_BIN)/python3: | $(VENV_PATH)
$(VENV_BIN)/pip3: | $(VENV_PATH)
$(VENV_BIN)/black: | $(VENV_PATH)
$(VENV_BIN)/pyemver: | $(VENV_PATH)

$(VENV_PATH)/bin/activate: $(VENV_PATH)

$(VENV_PATH):
	@python3 -m venv $(VENV_PATH)
	@. $(ACTIVATE) && $(PIP3) install -r requirements.txt 
	@. $(ACTIVATE) && $(PIP3) install -r requirements.dev.txt



.PHONY: pysemver
pysemver: $(PYTHON_PATH)/pysemver

$(PYTHON_PATH)/pysemver: pip-semver

.PHONY: black
black: $(PYTHON_PATH)/black

$(PYTHON_PATH)/black: pip-black

# Upload Targets

.PHONY: upload
upload: dist/$(PROJECT)-$(VERSION).tar.gz
upload: | $(VENV_PATH)
upload: | .pypirc
	@python3 -m twine upload --repository pypi dist/*$(VERSION)*
	
.pypirc:
	@ln ~/.pypirc .pypirc

install: $(PYTHON_PATH)/pip3
	@while [ $(PIP3) install $(PROJECT)==$(VERSION) ]; do sleep 5; done

# Global Python checks

.PHONY: pip3
pip3: python3
pip3: $(PYTHON_PATH)/pip3

$(PYTHON_PATH)/pip3:
	@python3 -m ensurepip --upgrade
	
.PHONY: python3
python3: python$(PYTHON_VERSION)

.PHONY: python$(PYTHON_VERSION)
python$(PYTHON_VERSION): $(PYTHON_PATH)/python$(PYTHON_VERSION)

$(PYTHON_PATH)/python$(PYTHON_VERSION):
	@echo "Could not find Python $(PYTHON_VERSION) in $(PYTHON_PATH)"
	@which python3 || echo "Could not find any python3 binary"
	@python3 --version | grep $(PYTHON_VERSION)
	@false

.PHONY: hooks
hooks: .git/hooks/pre-commit

.git/hooks/pre-commit: hooks/pre-commit
	@cp hooks/pre-commit .git/hooks/pre-commit
