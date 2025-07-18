# MangoTestingPlatform 芒果测试平台

✨ **概述**  
芒果测试平台是一款集UI、API和Pytest于一体的低代码测试平台。通过简单的配置即可完成UI和API自动化测试，无需编写代码，简单易用！  
- **支持的UI测试类型**：Web端、安卓、PC桌面，并且可以将多个操作组装成一个完整的测试用例。  
- **视频介绍&演示功能**：请先阅读帮助文档！  
- **执行端下载地址**：[点击下载执行端](https://www.alipan.com/s/8CmZdabwt4R)  

---

## 🚀 自动化功能介绍

### **UI自动化功能**
- 支持Web、安卓、PC桌面自动化测试。
- 提供录制功能，可快速生成测试步骤。
- 支持多种断言策略，用户可动态添加自定义断言方法。

### **API自动化功能**
- 支持接口测试、接口用例管理。
- 提供多种断言方式，支持动态添加断言方法。
- 支持接口参数化、前置/后置操作（如SQL、自定义脚本等）。

### **其他功能**
- 提供50多种断言策略，支持用户自定义断言方法。
- 支持测试用例参数化，灵活应对不同测试场景。
- 支持测试报告生成，便于分析测试结果。

---

## 📁 项目结构

### **MangoActuator**  
执行端，用于执行UI自动化测试用例。  
- 支持在任意电脑上运行，只需打开打包的exe文件即可执行UI自动化测试。

### **MangoServer**  
后端服务，提供API接口、任务调度、测试报告等功能。  
- 基于Django框架，支持RESTful API。
- 提供任务管理、测试用例管理、测试报告生成等核心功能。

### **mango-console**  
前端控制台，提供可视化界面进行测试用例管理、任务执行、报告查看等操作。  
- 基于Vue3 + TypeScript开发。
- 支持多主题、响应式布局，适配不同设备。

---

## 📦 功能演示

![功能演示GIF](功能演示.gif)

---

## 📄 许可证

本项目遵循MIT开源协议，详细信息请查看 [LICENSE](LICENSE) 文件。

---

## 🧩 支持的功能

- **UI自动化**：Web、安卓、PC桌面。
- **API自动化**：接口测试、参数化、断言。
- **Pytest集成**：支持Python测试框架集成。
- **测试报告**：支持Allure报告集成。
- **任务调度**：支持定时任务、手动触发任务。

---

## ❌ 不支持的功能

- 暂不支持移动端iOS自动化测试。
- 暂不支持分布式任务执行（后续版本计划支持）。

---

## 🛠️ 二次开发注意事项

- 项目基于Python + Django + Vue3开发，建议熟悉相关技术栈。
- 修改前端代码后需重新构建并部署至Nginx。
- 修改后端代码后需重启服务以生效。

---

## 📝 版权声明

版权所有 © 2022 by 芒果味

---

## 📞 支持与交流

添加作者微信，加入**芒果测试平台测试群**（备注：`git芒果测试平台`，否则可能无法通过验证）。

---

## 📸 项目截图

![项目截图](mango-console/public/static/images/screenshot.png)

---

## 📌 相关资源

- [执行端下载地址](https://www.alipan.com/s/8CmZdabwt4R)
- [帮助文档](https://example.com/help)

---

## 📬 联系方式

- **作者微信**：[扫码添加](author.jpg)
- **测试交流群**：[扫码加入](group.jpg)

---

## 📚 依赖项

- **后端**：Python 3.10+, Django 4.2+, DRF, Redis, MySQL
- **前端**：Vue3, TypeScript, Vite, Arco Design
- **执行端**：Playwright, Pytest, Appium（安卓支持）

---

## 📦 安装与部署

### 后端部署（MangoServer）

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 启动服务
python manage.py runserver 0.0.0.0:8000
```

### 前端部署（mango-console）

```bash
# 安装依赖
npm install

# 开发模式启动
npm run dev

# 构建生产环境包
npm run build
```

### 执行端部署（MangoActuator）

```bash
# 安装依赖
pip install -r requirements.txt

# 启动执行端
python main.py
```

---

## 📈 版本更新日志

请查看 [CHANGELOG.md](CHANGELOG.md)

---

## 📚 参考文档

- [Django官方文档](https://docs.djangoproject.com/)
- [Vue3官方文档](https://vuejs.org/)
- [Playwright官方文档](https://playwright.dev/)

---

## 🙌 贡献指南

欢迎提交PR或Issue！请遵循 [CONTRIBUTING.md](CONTRIBUTING.md) 中的贡献规范。

---

## 📄 致谢

感谢以下开源项目的支持：
- [Django](https://www.djangoproject.com/)
- [Vue.js](https://vuejs.org/)
- [Playwright](https://playwright.dev/)
- [Pytest](https://docs.pytest.org/en/latest/)

---

## 📬 联系我们

- **作者微信**：扫码添加（见 `author.jpg`）
- **测试交流群**：扫码加入（见 `group.jpg`）

---

## 📌 版本信息

当前版本：**v4.7.0**  
更新时间：**2025-04-13**

---

## 📚 附录

- [帮助文档](https://example.com/help)
- [API文档](https://example.com/api-docs)
- [测试用例编写规范](https://example.com/test-case-spec)

---

**感谢您使用芒果测试平台！**  
如有任何问题或建议，请随时联系作者或提交Issue。