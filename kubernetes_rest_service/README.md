# Kuberentes demo RESTful service

## Prerequisites
* Install [kubectl](https://kubernetes.io/ru/docs/tasks/tools/install-kubectl/)
* Install [minikube](https://kubernetes.io/ru/docs/tasks/tools/install-minikube/) for local development
* Install [helm](https://helm.sh/docs/intro/install/)

## How to run
_Make sure minikube is running in case of local k8s cluster is being used._

#### Use the chart directory:
```bash
cd ./chart
```

#### Add Bitnami helm repo (for PostgreSQL chart):
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
```

#### Update chart dependencies:
```bash
helm dep update
```

#### Install chart:
```
helm upgrade --install k8s-rest-service . -f values.yaml
```

#### Send HTTP requests to the service:
_You may need to edit /etc/hosts file for using arch.homework host name._

Create new user:
```bash
curl -X POST http://arch.homework/api/v1/users \
  --data '{"username": "new", "email": "foo@bar.example", "first_name": "Foo", "last_name": "Bar"}' \
  -H 'Content-Type: application/json' \
| jq
```

List existing users:
```bash
curl -X GET http://arch.homework/api/v1/users | jq
```

See also [Postman collection (v2.1)](https://github.com/stkrizh/otus/blob/master/kubernetes_rest_service/k8s-rest-service.postman_collection.json)
