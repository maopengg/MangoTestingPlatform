# ✨️ 概述

DrissionPage 是一个基于 python 的网页自动化工具。

它既能控制浏览器，也能收发数据包，还能把两者合而为一。

可兼顾浏览器自动化的便利性和 requests 的高效率。

它功能强大，内置无数人性化设计和便捷功能。

它的语法简洁而优雅，代码量少，对新手友好。

---

官方网站：[https://drissionpage.cn](https://drissionpage.cn)

<a href='https://gitee.com/g1879/DrissionPage/stargazers'><img src='https://gitee.com/g1879/DrissionPage/badge/star.svg?theme=dark' alt='star'></img></a> <a href='https://gitee.com/g1879/DrissionPage/members'><img src='https://gitee.com/g1879/DrissionPage/badge/fork.svg?theme=dark' alt='fork'></img></a>

项目地址：[gitee](https://gitee.com/g1879/DrissionPage)    |    [github](https://github.com/g1879/DrissionPage) 

您的星星是对我最大的支持💖

--- 

支持系统：Windows、Linux、Mac

python 版本：3.6 及以上

支持浏览器：Chromium 内核浏览器(如 Chrome 和 Edge)，electron 应用

---

# 🛠 如何使用

**📖 使用文档：**  [点击查看](https://g1879.gitee.io/drissionpagedocs)

**交流 QQ 群：**  636361957

---

# 💡 理念

简洁而强大！

--- 

# ☀️ 特性和亮点

作者经过长期实践，踩过无数坑，总结出的经验全写到这个库里了。

## 🎇 强大的自研内核

本库采用全自研的内核，内置无数实用功能，对常用功能作了整合和优化，对比 selenium，有以下优点：

- 不基于 webdriver
- 无需为不同版本的浏览器下载不同的驱动
- 运行速度更快
- 可以跨`<iframe>`查找元素，无需切入切出
- 把`<iframe>`看作普通元素，获取后可直接在其中查找元素，逻辑更清晰
- 可以同时操作浏览器中的多个标签页，即使标签页为非激活状态，无需切换
- 可以直接读取浏览器缓存来保存图片，无需用 GUI 点击另存
- 可以对整个网页截图，包括视口外的部分（90以上版本浏览器支持）
- 可处理非`open`状态的 shadow-root

## 🎇 亮点功能

除了以上优点，本库还内置了无数人性化设计。

- 极简的语法规则。集成大量常用功能，代码更优雅
- 定位元素更加容易，功能更强大稳定
- 无处不在的等待和自动重试功能。使不稳定的网络变得易于控制，程序更稳定，编写更省心
- 提供强大的下载工具。操作浏览器时也能享受快捷可靠的下载功能
- 允许反复使用已经打开的浏览器。无须每次运行从头启动浏览器，调试超方便
- 使用 ini 文件保存常用配置，自动调用，提供便捷的设置，远离繁杂的配置项
- 内置 lxml 作为解析引擎，解析速度成几个数量级提升
- 使用 POM 模式封装，可直接用于测试，便于扩展
- 高度集成的便利功能，从每个细节中体现
- 还有很多细节，这里不一一列举，欢迎实际使用中体验：）

--- 

# 🖐🏻 免责声明

禁止将 DrissionPage 应用到任何可能会违反法律规定和道德约束的项目中。  
友善使用 DrissionPage，遵守蜘蛛协议，禁止将 DrissionPage 用于任何可能有损他人的项目中。  
如您选择使用 DrissionPage 即代表您遵守此协议，作者不承担任何由于您违反此协议带来任何的法律风险和损失。  
同时，作者不对 DrissionPage 可能存在的缺陷导致的损失承担任何责任，一切后果由您承担。

---  

# ☕ 请我喝咖啡

如果本项目对您有所帮助，不妨请作者我喝杯咖啡 ：）

![](https://gitee.com/g1879/DrissionPageDocs/raw/master/static/img/code.jpg)