.PHONY: test lint image kind-up image-load deploy verify kind-down

IMAGE ?= secure-gitops-platform-portfolio:local
CLUSTER ?= secure-gitops
NAMESPACE ?= secure-platform
KUBE_CONTEXT ?= kind-$(CLUSTER)

test:
	python -m unittest discover -s app/tests -v

lint:
	python -m compileall -q app/src app/tests

image:
	docker build -t $(IMAGE) ./app

kind-up:
	kind create cluster --name $(CLUSTER) --config kind-config.yaml

image-load: image
	kind load docker-image $(IMAGE) --name $(CLUSTER)

deploy:
	helm upgrade --install platform-api ./helm/platform-api --kube-context $(KUBE_CONTEXT) \
		--namespace $(NAMESPACE) --create-namespace \
		--set image.repository=secure-gitops-platform-portfolio \
		--set image.tag=local \
		--set image.pullPolicy=IfNotPresent

verify:
	kubectl --context $(KUBE_CONTEXT) -n $(NAMESPACE) rollout status deployment/platform-api --timeout=120s
	kubectl --context $(KUBE_CONTEXT) -n $(NAMESPACE) get pods,service,hpa,pdb,networkpolicy

kind-down:
	kind delete cluster --name $(CLUSTER)
