Rainbow, a load-balancer service layer for IaaS provider.


## Service

Rainbow provide two kinds of api

1. Public API: public user api, user can operate their compute instances.
2. Manage API: private manager api, service provider can manage computing resources.

## Develop

``` bash
these convinient shell scripts can help to setup dev environment quickly.

cp ./env/env.sample env.local

# build docker image
./env/build.sh

# run the service
./env/start.sh

# stop service
./env/stop.sh
```
