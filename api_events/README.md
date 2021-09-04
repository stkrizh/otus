# Event-driven architecture demo app

## Prerequisites
* Install [kubectl](https://kubernetes.io/ru/docs/tasks/tools/install-kubectl/)
* Install [minikube](https://kubernetes.io/ru/docs/tasks/tools/install-minikube/) for local development
* Install [helm](https://helm.sh/docs/intro/install/)

## How to run
Start minikube:
```bash
minikube start --vm-driver=virtualbox
```
Enable minikube ingress addon:
```bash
minikube addons enable ingress
```
#### Use the chart directory:
```bash
cd ./chart
```

#### Add Bitnami helm repo (for PostgreSQL / RabbitMQ charts):
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
```

#### Update chart dependencies:
```bash
helm dep update
```

#### Install the chart
```bash
helm upgrade --install api-events . -f ./values.yaml
```
_Wait about 2-3 mins for all pods are ready._


#### Prepare /etc/hosts file
Add new line to `/etc/hosts` file:
```
$IP     arch.homework     
```
where `$IP` is output of:
```bash
minikube ip
```

#### Run API tests with newman:
```bash
newman run postman_collection.json
```
