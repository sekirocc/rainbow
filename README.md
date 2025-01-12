Rainbow 部署在每个集群，负责接收业务端请求，并对本地集群资源进行操作。

Rainbow 提供两种类型的API服务。

1. Public API：提供用户视角的资源操作接口，用户可用 SDK 直接调用。
2. Manage API：为 Boss, DevOps 等业务系统提供资源管理和信息聚合。

## Develop

``` bash
# 我们使用docker-compose及环境变量实现开发环境的搭建
# 根据本地开发环境，调整响应的 env.local 配置文件。
cp ./env/env.sample env.local

# Build Docker开发镜像
./env/build.sh

# 运行
./env/start.sh

# 停止
./env/stop.sh
```
