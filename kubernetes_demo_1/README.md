# Kubernetes demo application

## Prerequisites
* Install [kubectl](https://kubernetes.io/ru/docs/tasks/tools/install-kubectl/)
* Install [minikube](https://kubernetes.io/ru/docs/tasks/tools/install-minikube/) for local development

## How to run
Apply manifests:
```
kubectl apply -f ./manifests
```

Get ingress IP address with: 
```
kubectl get ingress
```

Send requests to the cluster (*111.222.33.4 it's IP address from output of previous command*):
```
curl -H "Host: arch.homework" -X GET 111.222.33.4/health
```
*Output:*
```
{"status": "OK"}

```
curl -H "Host: arch.homework" -X GET 111.222.33.4/otusapp/stanislav
```
*Output:*
```
{"name": "stanislav"}
```
