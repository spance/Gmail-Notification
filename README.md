# Gmail Notification

对已许可的Gmail邮箱进行检查，发现新邮件后通过已配置的短信接口发送未读邮件的提醒短信。

利用Google oauth接口访问已授权用户的收件箱，对未读邮件进行分析并发送提醒，同一未读邮件在6小时内不会提醒超过2次（未来这些策略参数可调整），避免长时间未读邮件造成大量短信的骚扰。

目前，通过console交互方式配置许可授权，在.conf文件中定义接口参数，自动通过cron-job做定时检查。

每5分钟检查一次，支持多账户，理论上最多可以配置3472222个用户，因为Google API允许每个Client每天可调用1亿次。

扫描和通信日志在logs目录下，请定时检查并反馈错误。

![sms](https://i.imgur.com/43WOaBe.png)

# 关于隐私和安全性

邮箱账户通常是私密性的，因此不建议使用第三方服务，应该将程序部署到可信服务器上，专属的为自己或朋友私密的运行。

Google oauth接口是安全、可靠的，程序通过Google接口获得用户授权，不接触密码，并且用户可随时在Google accounts中吊销授权。

考虑到存储安全，程序不会读取和存储任何邮件内容包括标题，仅通过邮件id做识别和分析。

考虑到传输安全，发送的短信中不含有与邮件相关的任何内容，仅包括未读邮件数量，并且mail地址经过了遮掩。

如果运行程序的服务器是安全的，则整个运作逻辑都是安全和可靠的。

# 配置和运行

1、客户端授权

首先，需要得到Google client credential，这是访问Google API的必要条件。
访问： https://console.developers.google.com/project
开启API并创建Client credential，然后下载json文件，命名并放置到`credentials\app_client_secret.json`

![g_api_1](https://i.imgur.com/5QM6vlc.png)
![g_api_2](https://i.imgur.com/rHUBFmU.png)

2、配置

取得一个可用的短信接口（应该基于http/https）及访问办法，请咨询你的短信接口服务商。
根据服务商提供的方法，配置到`gnoti.conf`中，通常都是GET或POST到服务商api地址。
详细配置说明请参看`gnoti.conf`中的注释说明。

3、部署应用

安装依赖关系：`pip install --upgrade google-api-python-client python-crontab`
将整个程序放置到具有读写权限的文件夹中，并运行`python gnoti.py --help`查看命令帮助。

![help](https://i.imgur.com/LrvpQqS.png)

4、账户授权

运行`python gnoti.py -a XXXX@gmail.com`以向导方式开始账户配置。
将会生成一个许可url，请账户所有者在其浏览器上执行并同意，将会跳到redirect_uri上（示例中配置到localhost上仅获取code部分）
再把Url上的code部分粘贴到console中，将会调用Google API获取授权。
再输入接收短信的电话号码，完成账户配置。

![setup](https://i.imgur.com/R0P8dbn.png)

一切无误后，程序将会每5分钟检查一次用户邮箱，未读且未被提醒超过2次的邮件，将会统计和发送提醒短信。

*注： 目前大陆是无法访问到Google Api的，因此不要在国内服务器上部署。