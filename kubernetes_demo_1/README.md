Kubernetes demo application

## How to run
Apply manifests:
```
kubectl apply -f ./manifests
```

Get ingress IP address with: 
```
kubectl get ingress
```

Send requests to the cluster:
```
# 111.222.33.4 it's IP address from output of previous command

curl -H "Host: arch.homework" -X GET 111.222.33.4/health

curl -H "Host: arch.homework" -X GET 111.222.33.4/otusapp/stanislav
```