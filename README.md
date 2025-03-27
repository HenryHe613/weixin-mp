# weixin-mp


## deploy by docker

[Here](https://hub.docker.com/repository/docker/henryhe613/weixin-mp/general)

## Introduction

这个项目是仿造Server酱或者传息的一个开源项目，可以把公众号（其实是服务号）变成一个推送消息的平台。

## Environment

 - APPID: 公众号APPID，在后台找到
 - APPSECRET: 公众号APPSECRET，在后台找到
 - OPENID: 接收消息的用户的OPENID，暂时没用
 - TEMPLATE_ID: 消息模版的ID，需要微信认证后申请
 - VERIFY_TOKEN: 验证token，用于微信服务器验证
 - WEB_PORT: web服务端口，用于微信服务器验证并提供api让微信服务器/客户调用
 - REDIS_HOST=127.0.0.1
 - REDIS_PORT=6379
 - REDIS_DB=0


## 公众号命令

 - `/id` 获取用户的openid
 - `/group`
   - `/group list` 列出创建的群组和加入的群组
   - `/group create <name>` 创建一个群组
   - `/group delete <name>` 删除一个群组
   - `/group join <name>` 加入一个群组
   - `/group leave <name>` 离开一个群组
   - `/group add <name> <openid>` 添加一个用户到群组（不打算实现）
   - `/group remove <name> <openid>` 从一个群组删除一个用户（不打算实现）
 - `/info` 查看用户信息（不打算实现）