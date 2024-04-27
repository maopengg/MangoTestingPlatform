###### 检查环境
```json
python==3.10.4
```
```json
node==16.13.1
```
```json
npm==8.1.2
```
注意：以上版本可以大于，python不可小于3.10，node不可小于16，npm不清楚是否可小于
###### 克隆代码
```shell
git clone https://gitee.com/mao-peng/MangoTestingPlatform.git
```
###### 注意项

- 首次启动，需要手动添加一个账号，才可以登录（后续会想办法增加一个默认账号）
- 首次启动需要先运行执行器，点击发送缓存数据，否则web页面无法选择元素操作和断言
- 可以使用sqlite作为数据源，但是不清楚会发生什么错误
- 所有部署的命令，都是在idea的终端进行输入。如果没有，则进入到项目主目录再输入命令。后端记得选择了虚拟环境，才能输入
- 不可以自己随意安装版本，否则会出现不兼容的问题，你能解决依赖包不兼容就随意安装
### MangoServer
###### 删除历史迁移文件（后面会采用分支的方式来进行管理）
```json
MangoServer/PyAutoTest/auto_test/auto_api/migrations
MangoServer/PyAutoTest/auto_test/auto_system/migrations
MangoServer/PyAutoTest/auto_test/auto_ui/migrations
MangoServer/PyAutoTest/auto_test/auto_user/migrations
以上四个目录中，除了__init__.py，其他文件都得删掉
```
###### 配置虚拟环境
```shell
-
```
###### 安装依赖包
```shell
 pip install -r .\requirements.txt
```
注意：不可以自己随意安装版本，否则会出现不兼容的问题，你能解决依赖包不兼容就随意安装
###### 配置mysql

- mysql版本要求：5.6及以上
- 数据库类型：utf8mb4_general_ci

![image.png](https://cdn.nlark.com/yuque/0/2024/png/21370366/1710820868721-f095a0d7-ab08-46e5-ae2a-a55fa92d978e.png#averageHue=%235e784b&clientId=uf4d83e2d-68a1-4&from=paste&height=165&id=u3ddc27d9&originHeight=454&originWidth=1201&originalType=binary&ratio=1&rotation=0&showTitle=false&size=87515&status=done&style=none&taskId=uf1ff6577-3c13-42fc-9181-f6ac88356ac&title=&width=437)
###### 迁移数据库
```shell
python manage.py makemigrations
python manage.py migrate
```
###### 新建django执行服务或运行命令启动django
![image.png](https://cdn.nlark.com/yuque/0/2024/png/21370366/1710820789045-0fa6e144-ab1f-422a-a57d-206033395dfc.png#averageHue=%233d4144&clientId=uf4d83e2d-68a1-4&from=paste&height=177&id=ud44df47d&originHeight=676&originWidth=1044&originalType=binary&ratio=1&rotation=0&showTitle=false&size=48473&status=done&style=none&taskId=u01795bff-bc41-4b1d-ad6f-abcfc071291&title=&width=274)
或
```shell
{{虚拟环境目录}}\MangoServer\Scripts\python.exe {{git拉下来的目录}}/MangoTestingPlatform/MangoServer/manage.py runserver 8000
```
注意：红色：虚拟环境目录，黄色：git项目
###### 首次部署，需要手动创建账号
```plsql
INSERT INTO `test-mango-server`.`user` (`id`, `create_time`, `update_time`, `nickname`, `username`, `password`, `ip`, `mailbox`, `role_id`, `last_login_time`, `selected_environment`, `selected_project`) VALUES (1, '2023-07-13 12:45:09.000000', '2024-03-18 07:23:50.208346', '毛鹏', '18071710220', 'e10adc3949ba59abbe56e057f20f883e', '171.113.40.173:5402', '729164035@qq.com', null, '2024-03-18 07:23:50.208173', null, null);
```
注意：请修改插入语句中的红色内容为你自己；黄色内容是密码，md5小写加密，默认是：123456
### mango-console
###### 安装依赖包
```shell
npm i
```
###### 启动项目
```shell
npm run dev
```

### MangoActuator
###### 配置虚拟环境
###### 安装依赖包
```shell
 pip install -r .\requirements.txt
```
###### 启动项目
```
执行：执行器.py  文件即可
```
###### 首次启动注意
```
需要点击：缓存数据按钮，发送数据，否则web页面无法获取元素的操作类型
```
### 以上步骤做完之后，把以下sql进行执行，可快速体验API和UI自动化！
[初始化.sql](https://www.yuque.com/attachments/yuque/0/2024/sql/21370366/1714214963092-f0b0b1a0-f1a9-45aa-8b7a-b53d82494312.sql?_lake_card=%7B%22src%22%3A%22https%3A%2F%2Fwww.yuque.com%2Fattachments%2Fyuque%2F0%2F2024%2Fsql%2F21370366%2F1714214963092-f0b0b1a0-f1a9-45aa-8b7a-b53d82494312.sql%22%2C%22name%22%3A%22%E5%88%9D%E5%A7%8B%E5%8C%96.sql%22%2C%22size%22%3A68526%2C%22ext%22%3A%22sql%22%2C%22source%22%3A%22%22%2C%22status%22%3A%22done%22%2C%22download%22%3Atrue%2C%22taskId%22%3A%22u23ecbf43-f6e9-4f61-9581-ae8e1e91614%22%2C%22taskType%22%3A%22upload%22%2C%22type%22%3A%22%22%2C%22__spacing%22%3A%22both%22%2C%22id%22%3A%22ua5d51e3a%22%2C%22margin%22%3A%7B%22top%22%3Atrue%2C%22bottom%22%3Atrue%7D%2C%22card%22%3A%22file%22%7D)
