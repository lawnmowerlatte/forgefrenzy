ifeq (, $(shell command -v python3))
$(error "Python3 is not installed")
endif

PROJECT = forgefrenzy
SOURCES = $(wildcard src/$(PROJECT)/*.py)
VERSION = $(shell cat VERSION)

PYTHON_VERSION = 3.10
PYTHON3 = python$(PYTHON_VERSION)
PIP3 = pip3
PYTHON_PATH = $(shell dirname $(shell command -v python3))
TERRAFORM_BIN = $(shell which terraform)
TERRAFORM = $(shell which terraform) -chdir=terraform/

VENV_PATH = .venv
VENV_BIN = $(VENV_PATH)/bin
VPYTHON3 = $(VENV_BIN)/$(PYTHON3)
VPIP3 = $(VENV_BIN)/$(PIP3)

export PYTHONPATH = src

.PHONY: all
all: pip
localdev: hooks test build
pip: hooks test VERSION build upload install
deploy: hooks test build terraform

.PHONY: docker
docker: | docker-image
docker: docker-run
docker: docker-test

docker-image: $(SOURCES)
docker-image: TARGET ?= handler
	@docker build --target=$(TARGET) -t forgefrenzy-lambda:latest -f docker/lambda/Dockerfile .

docker-run: docker-stop
	@docker run -p 8000:8000 -t forgefrenzy-lambda:latest &
	@sleep 2

docker-stop:
	@docker ps | grep 0.0.0.0:8000 | cut -f 1 -d ' ' | xargs -I{} docker stop {}

docker-test: METHOD ?= GET
docker-test: DATA ?= {}
# docker-test: _HANDLER ?= forgefrenzy.gateway.lambda.handler
docker-test:
	curl -XPOST "http://localhost:8000/2015-03-31/functions/function/invocations" -d "$(DATA)"

lambda:
	@$(VPYTHON3) -m forgefrenzy.gateway.lambda


.PHONY: renew
renew: terraform/certificates/certbot
renew:
	@certbot renew \
	    --logs-dir terraform/certificates/certbot/logs \
	    --work-dir terraform/certificates/certbot \
	    --config-dir terraform/certificates/certbot

.PHONY: certificates
certificates: terraform/certificates/public.pem
certificates: terraform/certificates/private.pem
certificates: terraform/certificates/chain.pem

terraform/certificates/certbot:
	@certbot certonly --standalone -d forgefrenzy.lawnmowerlatte.com \
        --logs-dir terraform/certificates/certbot/logs \
        --workdir terraform/certificates/certbot \
        --config-dir terraform/certificates/certbot
	@$(MAKE) certificates

terraform/certificates/public.pem: terraform/certificates/certbot
terraform/certificates/public.pem:
	@ln -sf `pwd`/terraform/certificates/certbot/live/forgefrenzy.lawnmowerlatte.com/cert.pem terraform/certificates/public.pem

terraform/certificates/private.pem: terraform/certificates/certbot
terraform/certificates/private.pem:
	@ln -sf `pwd`/terraform/certificates/certbot/live/forgefrenzy.lawnmowerlatte.com/privkey.pem terraform/certificates/private.pem

terraform/certificates/chain.pem: terraform/certificates/certbot
terraform/certificates/chain.pem:
	@ln -sf `pwd`/terraform/certificates/certbot/live/forgefrenzy.lawnmowerlatte.com/fullchain.pem terraform/certificates/chain.pem


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
test: $(VPYTHON3)
test: format
test:
	@$(VPYTHON3) -m $(PROJECT) --test
	@$(VPYTHON3) -m $(PROJECT).blueplate.special --test

.PHONY: format
format: $(VENV_BIN)/black
	@$(VENV_BIN)/black src/

# Build targets 
.PHONY: clean
clean:
	@rm -rf dist/

# Remove sqlite tables
.PHONY: empty
empty:
	find . -name "*.sqlite"

.PHONY: build
build: VERSION
build: dist/forgefrenzy-$(VERSION).tar.gz

.PHONY: run
run: ARGS ?= "-vv"
run:
	@echo "$(VPYTHON3) -m $(PROJECT) $(ARGS)"
	@$(VPYTHON3) -m $(PROJECT) $(ARGS)

$(SOURCES):
	@echo "Sources have changed..."

dist/$(PROJECT)-$(VERSION)-py3-none-any.whl: dist/$(PROJECT)-$(VERSION).tar.gz

dist/forgefrenzy-$(VERSION).tar.gz: $(SOURCES)
	@$(VPYTHON3) -m build

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
$(VPYTHON3): | $(VENV_PATH)
$(VPIP3): | $(VENV_PATH)
$(VENV_BIN)/black: | $(VENV_PATH)
$(VENV_BIN)/pyemver: | $(VENV_PATH)

$(VENV_PATH): $(PYTHON3)
$(VENV_PATH): $(PIP3)
$(VENV_PATH): $(PYTHON3)
	@$(PYTHON_PATH)/$(PYTHON3) -m venv $(VENV_PATH)
	@$(VPYTHON3) --version | grep $(PYTHON_VERSION) > /dev/null \
	    || (echo "The virtual environment is not running Python $(PYTHON_VERSION)" && false)
	@$(VPIP3) install -r requirements.txt
	@$(VPIP3) install -r requirements.dev.txt
	@$(VPIP3) install -r docker/lambda/requirements.txt

.PHONY: venv
venv: no_venv
venv: $(VENV_PATH)

.PHONY: no_venv
no_venv:
	rm -rf $(VENV_PATH)

# Upload Targets

.PHONY: upload
upload: dist/$(PROJECT)-$(VERSION).tar.gz
upload: | $(VENV_PATH)
upload: | .pypirc
	@python3 -m twine upload --repository pypi dist/*$(VERSION)*
	
.pypirc:
	@ln ~/.pypirc .pypirc

install: $(PYTHON_PATH)/$(PIP3)
    # Installs the package in the outer context virtual env
    # This handles nested virtualenvs
	@while ! $(shell dirname $(shell readlink $(VENV_BIN)/$(PYTHON3)))/$(PIP3) install $(PROJECT)==$(VERSION); do sleep 5; done

# Global Python checks

.PHONY: $(PIP3)
$(PIP3): $(PYTHON3)
$(PIP3): $(PYTHON_PATH)/$(PIP3)

$(PYTHON_PATH)/$(PIP3):
	@$(PYTHON_PATH)/$(PYTHON3) -m ensurepip --upgrade

.PHONY: python3
python3: $(PYTHON3)

.PHONY: $(PYTHON3)
$(PYTHON3): $(PYTHON_PATH)/$(PYTHON3)

$(PYTHON_PATH)/$(PYTHON3):
	@echo "Could not find Python $(PYTHON_VERSION) in $(PYTHON_PATH)!"

.PHONY: hooks
hooks: .git/hooks/pre-commit

.git/hooks/pre-commit: hooks/pre-commit
	@cp hooks/pre-commit .git/hooks/pre-commit
