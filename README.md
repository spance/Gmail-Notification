# Gmail Notification

对已授权的Gmail邮箱检查分析，发现新邮件后发送未读提醒短信（通过配置的短信接口）。

利用Google oauth接口和授权凭证查询收件箱，对未读邮件进行分析，同一未读邮件在6小时内不会提醒超过2次（未来这些策略参数可调整），避免重复短信的困扰。

每5分钟检查一次，支持多账户，理论上最多可以配置3472222个用户，因为Google API允许每个Client每天可调用1亿次。

扫描和通信日志在logs目录下，请定时检查并[反馈错误](https://github.com/spance/Gmail-Notification/issues)。

![sms](https://i.imgur.com/43WOaBe.png)

# 适用场景

- 不想公开Gmail密码给第三方的
- 不能/不便持续Gmail在线的
- 不想使用邮件客户端残留邮件副本
- 想要更及时的通知
- 想要更爽的自定义通知
- 想要更安全、更具隐私性的方式

本方案就是考虑上面的场景需求，做专业的私人定制。

# 关于隐私和安全性

邮箱通常是高度隐私和保密的，因此强烈不建议使用第三方成品服务。

应将该开源程序部署到可信服务器上，专属为自己或亲朋好友安全私密的运行。

Google oauth接口是安全、可靠的，程序通过Google接口获得用户授权，不接触密码，并且用户可随时在Google accounts中吊销授权。

考虑到存储安全，程序不会读取和存储任何邮件内容包括标题，仅通过邮件id做识别和分析。

考虑到传输安全，发送的短信中不含有与邮件相关的任何内容，仅包括未读数量，并对mail地址做了遮掩。

如果运行程序的服务器是安全的，则整个运作逻辑都是安全和可靠的。

# 运行条件

1. 一个可访问Google和可运行Python程序的Linux环境
2. 一个基于http/https的短信接口

该应用是开源免费的，但所需的两个运行条件可能需要向相应的服务商购买。

*注： 不要在国内服务器上部署（无法访问Google API）。*

# 配置和运行

目前通过console交互配置许可授权，在.conf中配置接口参数，自动通过cron-job做定时检查。

**1、客户端授权**

首先，需要得到Google client credential，这是允许该程序访问Google的必要条件。

访问： https://console.developers.google.com/project

开启API并创建Client Credential，然后下载json文件，命名并放置到`credentials\app_client_secret.json`

![g_api_1](https://i.imgur.com/5QM6vlc.png)
![g_api_2](https://i.imgur.com/rHUBFmU.png)

**2、配置**

请咨询短信接口服务商，根据服务商提供的方法，配置到`gnoti.conf`中，通常都是GET或POST到服务商api地址。

详细配置说明请参看`gnoti.conf`中的注释说明。

**3、部署应用**

安装依赖关系：`sudo pip install --upgrade google-api-python-client python-crontab`

将整个程序放置到具有读写权限的文件夹中，并运行`python gnoti.py --help`查看命令帮助。

![help](https://i.imgur.com/LrvpQqS.png)

**4、账户授权**

运行`python gnoti.py -a XXXX@gmail.com`以向导方式开始账户配置。

将生成一个许可Url，请账户所有者在其浏览器上执行并同意，将会跳到redirect_uri上（示例中配置到localhost上仅获取code部分）

再取其code部分粘贴到console中，将会调用Google API获取授权。

再输入接收短信的电话号码，完成账户配置。

![setup](https://i.imgur.com/R0P8dbn.png)

一切无误后，程序将会每5分钟检查一次用户邮箱，未读且未被提醒超过2次的邮件（参照策略），将会统计和发送提醒短信。
