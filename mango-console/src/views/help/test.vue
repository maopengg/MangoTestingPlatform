<template>
</template>

<script setup lang="ts">
  import { onMounted, ref, reactive } from 'vue'

  const summary = reactive({
    "count": 3,
    "fail_count": 0,
    "success_count": 2,
    "stay_begin_count": 0,
    "proceed_count": 1,
    "api_count": 1,
    "ui_count": 1,
    "pytest_count": 1
  })
  const report_data =   reactive([
  {
    "id": 82,
    "create_time": "2025-03-09 22:23:11",
    "update_time": "2025-03-11 10:49:36",
    "project_product": {
      "id": 2,
      "create_time": "2024-11-24 19:58:25",
      "update_time": "2024-11-26 21:24:46",
      "project": {
        "id": 1,
        "create_time": "2024-11-24 00:38:16",
        "update_time": "2024-11-24 00:38:22",
        "name": "演示DEMO",
        "status": 1
      },
      "name": "玩安卓",
      "ui_client_type": 0,
      "api_client_type": 0
    },
    "test_suite": {
      "id": 232853768174,
      "create_time": "2025-03-09 22:23:11",
      "update_time": "2025-03-11 10:49:36",
      "test_env": 2,
      "status": 3,
      "is_notice": 0,
      "project_product": 2,
      "user": 1,
      "tasks": 9
    },
    "type": 0,
    "test_env": 2,
    "case_id": 3,
    "case_name": "登录后退出登录",
    "status": 3,
    "error_message": "页面无元素：用户名 表达式：get_by_role(\"link\", name=\"mango_test\")",
    "result_data": [
      {
        "id": 6,
        "name": "登录账号",
        "type": 0,
        "status": 1,
        "equipment": {
          "type": 0,
          "web_h5": null,
          "web_max": false,
          "web_path": "C:\\Users\\毛鹏\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe",
          "web_type": 0,
          "win_path": null,
          "host_list": null,
          "win_title": null,
          "web_headers": false,
          "web_parallel": 5,
          "and_equipment": null,
          "web_recording": false,
          "is_header_intercept": null
        },
        "cache_data": {
          "key": "value",
          "密码A": "123456",
          "账号A": "mango_test"
        },
        "test_object": {
          "url": "https://www.wanandroid.com/blog/show/2",
          "package_name": null
        },
        "error_message": null,
        "project_product_id": 2,
        "element_result_list": [
          {
            "id": 11,
            "exp": 2,
            "key": null,
            "loc": "locator(\"a\").filter(has_text=re.compile(r\"^登录$\"))",
            "sql": null,
            "sub": null,
            "name": "登录",
            "type": 0,
            "sleep": null,
            "value": null,
            "actual": null,
            "expect": null,
            "status": 1,
            "ope_key": "w_click",
            "key_list": null,
            "ope_value": "{'locating': <Locator frame=<Frame name= url='https://www.wanandroid.com/blog/show/2'> selector='a >> internal:has-text=/^登录$/'>}",
            "ele_quantity": 1,
            "picture_path": null,
            "error_message": null
          },
          {
            "id": 12,
            "exp": 2,
            "key": null,
            "loc": "get_by_role(\"textbox\", name=\"请输入用户名\")",
            "sql": null,
            "sub": null,
            "name": "账号输入框",
            "type": 0,
            "sleep": null,
            "value": null,
            "actual": null,
            "expect": null,
            "status": 1,
            "ope_key": "w_input",
            "key_list": null,
            "ope_value": "{'locating': <Locator frame=<Frame name= url='https://www.wanandroid.com/blog/show/2'> selector='internal:role=textbox[name=\"请输入用户名\"i]'>, 'input_value': '${username}'}",
            "ele_quantity": 1,
            "picture_path": null,
            "error_message": null
          },
          {
            "id": 13,
            "exp": 2,
            "key": null,
            "loc": "get_by_role(\"textbox\", name=\"请输入密码\")",
            "sql": null,
            "sub": null,
            "name": "密码输入框",
            "type": 0,
            "sleep": null,
            "value": null,
            "actual": null,
            "expect": null,
            "status": 1,
            "ope_key": "w_input",
            "key_list": null,
            "ope_value": "{'locating': <Locator frame=<Frame name= url='https://www.wanandroid.com/blog/show/2'> selector='internal:role=textbox[name=\"请输入密码\"i]'>, 'input_value': '${password}'}",
            "ele_quantity": 1,
            "picture_path": null,
            "error_message": null
          },
          {
            "id": 14,
            "exp": 2,
            "key": null,
            "loc": "locator(\"#loginDialog div\").get_by_text(\"登录\")",
            "sql": null,
            "sub": null,
            "name": "确认登录",
            "type": 0,
            "sleep": null,
            "value": null,
            "actual": null,
            "expect": null,
            "status": 1,
            "ope_key": "w_click",
            "key_list": null,
            "ope_value": "{'locating': <Locator frame=<Frame name= url='https://www.wanandroid.com/blog/show/2'> selector='#loginDialog div >> internal:text=\"\\\\u767b\\\\u5f55\"i'>}",
            "ele_quantity": 1,
            "picture_path": null,
            "error_message": null
          },
          {
            "id": 21,
            "exp": 2,
            "key": "key",
            "loc": "locator(\"#kw\")",
            "sql": null,
            "sub": null,
            "name": "输入框",
            "type": 3,
            "sleep": null,
            "value": "value",
            "actual": null,
            "expect": null,
            "status": 1,
            "ope_key": null,
            "key_list": null,
            "ope_value": null,
            "ele_quantity": 0,
            "picture_path": null,
            "error_message": null
          }
        ],
        "case_step_details_id": 6,
        "project_product_name": "玩安卓"
      },
      {
        "id": 7,
        "name": "退出登录",
        "type": 0,
        "status": 0,
        "equipment": {
          "type": 0,
          "web_h5": null,
          "web_max": false,
          "web_path": "C:\\Users\\毛鹏\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe",
          "web_type": 0,
          "win_path": null,
          "host_list": null,
          "win_title": null,
          "web_headers": false,
          "web_parallel": 5,
          "and_equipment": null,
          "web_recording": false,
          "is_header_intercept": null
        },
        "cache_data": {
          "key": "value",
          "密码A": "123456",
          "账号A": "mango_test"
        },
        "test_object": {
          "url": "https://www.wanandroid.com/blog/show/2",
          "package_name": null
        },
        "error_message": "页面无元素：用户名 表达式：get_by_role(\"link\", name=\"mango_test\")",
        "project_product_id": 2,
        "element_result_list": [
          {
            "id": 15,
            "exp": 2,
            "key": null,
            "loc": "get_by_role(\"link\", name=\"mango_test\")",
            "sql": null,
            "sub": null,
            "name": "用户名",
            "type": 0,
            "sleep": null,
            "value": null,
            "actual": null,
            "expect": null,
            "status": 0,
            "ope_key": "w_hover",
            "key_list": null,
            "ope_value": null,
            "ele_quantity": 0,
            "picture_path": "files/失败截图-用户名1741532358000.jpg",
            "error_message": "页面无元素：用户名 表达式：get_by_role(\"link\", name=\"mango_test\")"
          }
        ],
        "case_step_details_id": 7,
        "project_product_name": "玩安卓"
      }
    ],
    "retry": 3,
    "push_time": "2025-03-11T10:49:36.989542"
  },
  {
    "id": 81,
    "create_time": "2025-03-09 22:23:11",
    "update_time": "2025-03-10 13:09:49",
    "project_product": {
      "id": 2,
      "create_time": "2024-11-24 19:58:25",
      "update_time": "2024-11-26 21:24:46",
      "project": {
        "id": 1,
        "create_time": "2024-11-24 00:38:16",
        "update_time": "2024-11-24 00:38:22",
        "name": "演示DEMO",
        "status": 1
      },
      "name": "玩安卓",
      "ui_client_type": 0,
      "api_client_type": 0
    },
    "test_suite": {
      "id": 232853768174,
      "create_time": "2025-03-09 22:23:11",
      "update_time": "2025-03-11 10:49:36",
      "test_env": 2,
      "status": 3,
      "is_notice": 0,
      "project_product": 2,
      "user": 1,
      "tasks": 9
    },
    "type": 1,
    "test_env": 2,
    "case_id": 2,
    "case_name": "正确的账号错误的密码",
    "status": 1,
    "error_message": null,
    "result_data": [
      {
        "id": 5,
        "ass": [],
        "name": "首页相关",
        "status": 1,
        "request": {
          "url": "https://www.wanandroid.com/article/list/0/json",
          "data": null,
          "file": null,
          "json": null,
          "method": "GET",
          "params": null,
          "headers": {
            "cookie": "JSESSIONID=71D8A4BB60E34325A00B0D178C05C765; Path=/; Secure; HttpOnly, loginUserName=mango_test; Expires=Wed, 09-Apr-2025 05:09:49 GMT; Path=/, token_pass=5d9b90bcb70640183e09d1e755ead823; Expires=Wed, 09-Apr-2025 05:09:49 GMT; Path=/, loginUserName_wanandroid_com=mango_test; Domain=wanandroid.com; Expires=Wed, 09-Apr-2025 05:09:49 GMT; Path=/, token_pass_wanandroid_com=5d9b90bcb70640183e09d1e755ead823; Domain=wanandroid.com; Expires=Wed, 09-Apr-2025 05:09:49 GMT; Path=/"
          }
        },
        "response": {
          "code": 200,
          "json": {
            "data": {
              "over": false,
              "size": 20,
              "datas": [
                {
                  "id": 29628,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://juejin.cn/post/7478994020612374543",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": true,
                  "title": "该怎么学Android进阶，拒绝沦为高级三方SDK调用工程师？",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 161755,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "21分钟前",
                  "chapterId": 502,
                  "shareDate": 1741582098000,
                  "shareUser": "wgllss",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1741582098000,
                  "selfVisible": 0,
                  "niceShareDate": "21分钟前",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29627,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://blog.csdn.net/qq_40533422/article/details/146093982",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": true,
                  "title": "Android 仿 DeepSeek 思考效果：逐字显示 AI 生成内容，支持加粗、颜色，复制内容",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 9296,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "4小时前",
                  "chapterId": 502,
                  "shareDate": 1741567871000,
                  "shareUser": "JasonYin",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1741567871000,
                  "selfVisible": 0,
                  "niceShareDate": "4小时前",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29606,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://www.wanandroid.com/blog/show/3750",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "Android 技术周刊 （2025-03-01 ~ 2025-03-08）",
                  "author": "张鸿洋",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": -1,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2天前",
                  "chapterId": 543,
                  "shareDate": 1741363800000,
                  "shareUser": "",
                  "isAdminAdd": false,
                  "chapterName": "Android技术周报",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1741363200000,
                  "selfVisible": 0,
                  "niceShareDate": "2天前",
                  "superChapterId": 543,
                  "superChapterName": "技术周报",
                  "realSuperChapterId": 542
                },
                {
                  "id": 29605,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://blog.csdn.net/u013290250/article/details/145769573",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "Flutter&mdash;&mdash;更详细原生交互（MethodChannel、EventChannel、BasicMessageChannel）使用教程",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 149113,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2天前",
                  "chapterId": 502,
                  "shareDate": 1741326281000,
                  "shareUser": "duangduang",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1741326281000,
                  "selfVisible": 0,
                  "niceShareDate": "2天前",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29604,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://mp.weixin.qq.com/s/b6d2vupUG0TtM0l-jsgIHQ",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "Android分屏功能原理（基于Android12L）",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 12467,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-03-07 12:29",
                  "chapterId": 502,
                  "shareDate": 1741321786000,
                  "shareUser": "残页",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1741321786000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-03-07 12:29",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29510,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://juejin.cn/post/7469809220646010916",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "记一次无障碍测试引发app崩溃问题的排查与解决在APP发版前，我们一般都会先跑mtc的自动化测试框架，也就是让脚本模拟用",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 2,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-03-02 11:14",
                  "chapterId": 502,
                  "shareDate": 1740839799000,
                  "shareUser": "鸿洋",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1740885244000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-03-01 22:36",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29508,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://www.wanandroid.com/blog/show/3747",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "Android 技术周刊 （2025-02-22 ~ 2025-03-01）",
                  "author": "张鸿洋",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": -1,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-03-01 00:00",
                  "chapterId": 543,
                  "shareDate": 1740759000000,
                  "shareUser": "",
                  "isAdminAdd": false,
                  "chapterName": "Android技术周报",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1740758400000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-03-01 00:10",
                  "superChapterId": 543,
                  "superChapterName": "技术周报",
                  "realSuperChapterId": 542
                },
                {
                  "id": 29506,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://juejin.cn/post/7475575836705898533",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "2025年Android六边形战士开发趋势，需要掌握哪些技能可自我反省",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 161755,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-27 09:00",
                  "chapterId": 502,
                  "shareDate": 1740618053000,
                  "shareUser": "wgllss",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1740618053000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-27 09:00",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29494,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://www.wanandroid.com/blog/show/3745",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "Android 技术周刊 （2025-02-15 ~ 2025-02-22）",
                  "author": "张鸿洋",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": -1,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-22 00:00",
                  "chapterId": 543,
                  "shareDate": 1740154200000,
                  "shareUser": "",
                  "isAdminAdd": false,
                  "chapterName": "Android技术周报",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1740153600000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-22 00:10",
                  "superChapterId": 543,
                  "superChapterName": "技术周报",
                  "realSuperChapterId": 542
                },
                {
                  "id": 29493,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://juejin.cn/post/7471630643534512164",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "我写了个App，上架 Google Play 一年，下载不到 10 次，于是决定把它开源了",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 2470,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-21 17:43",
                  "chapterId": 502,
                  "shareDate": 1740131039000,
                  "shareUser": "ldlywt",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1740131039000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-21 17:43",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29492,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://www.bilibili.com/video/BV1bs421N7tR/?spm_id_from=888.80997.embed_other.whitelist&amp;t=15.406298&amp;bvid=BV1bs421N7tR&amp;vd_source=f43def12c6eccac37abb1f5d026db37a",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "通往AGI之路分享：AI Agent-Coze搭建 5月8日",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 2,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-20 21:43",
                  "chapterId": 502,
                  "shareDate": 1740058980000,
                  "shareUser": "鸿洋",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1740058980000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-20 21:43",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29490,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://juejin.cn/post/7472223022192836659",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "Android拦截其它播放声音：内录音，外录音，录屏，剪辑，混音，一键制作大片全搞定",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 161755,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-17 17:44",
                  "chapterId": 502,
                  "shareDate": 1739785477000,
                  "shareUser": "wgllss",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1739785477000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-17 17:44",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29488,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://www.wanandroid.com/blog/show/3743",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "Android 技术周刊 （2025-02-08 ~ 2025-02-15）",
                  "author": "张鸿洋",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": -1,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-15 00:00",
                  "chapterId": 543,
                  "shareDate": 1739549400000,
                  "shareUser": "",
                  "isAdminAdd": false,
                  "chapterName": "Android技术周报",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1739548800000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-15 00:10",
                  "superChapterId": 543,
                  "superChapterName": "技术周报",
                  "realSuperChapterId": 542
                },
                {
                  "id": 29487,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://juejin.cn/post/7469991575277207602",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "元宵节前福利，神之操作，一键下载想要的同类型多个图片？？",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 161755,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-13 20:56",
                  "chapterId": 502,
                  "shareDate": 1739451373000,
                  "shareUser": "wgllss",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1739451373000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-13 20:56",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29480,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://zhuanlan.zhihu.com/p/708244292",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "鸿蒙内核论文阅读",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 12467,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-10 11:55",
                  "chapterId": 502,
                  "shareDate": 1739159716000,
                  "shareUser": "残页",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1739159721000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-10 11:55",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29479,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://blog.csdn.net/qq_40533422/article/details/144839240",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "HarmonyOSNEXT实战:搭建模块化项目架构，附完整代码仓",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 9296,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-10 08:45",
                  "chapterId": 502,
                  "shareDate": 1739148322000,
                  "shareUser": "JasonYin",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1739148322000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-10 08:45",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29484,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://mp.weixin.qq.com/s/_zlJeB1xYm7grr9w8WSsfA",
                  "tags": [
                    {
                      "url": "/wxarticle/list/408/1",
                      "name": "公众号"
                    }
                  ],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "再学安卓 - binder之Framework通信流程",
                  "author": "鸿洋",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": -1,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-10 00:00",
                  "chapterId": 408,
                  "shareDate": 1739176247000,
                  "shareUser": "",
                  "isAdminAdd": false,
                  "chapterName": "鸿洋",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1739116800000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-10 16:30",
                  "superChapterId": 408,
                  "superChapterName": "公众号",
                  "realSuperChapterId": 407
                },
                {
                  "id": 29476,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://juejin.cn/post/7468865451134091275",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "Android之等级金字塔之Compose智能实现",
                  "author": "",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": 161755,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-08 15:47",
                  "chapterId": 502,
                  "shareDate": 1739000821000,
                  "shareUser": "wgllss",
                  "isAdminAdd": false,
                  "chapterName": "自助",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1739000821000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-08 15:47",
                  "superChapterId": 494,
                  "superChapterName": "广场Tab",
                  "realSuperChapterId": 493
                },
                {
                  "id": 29474,
                  "zan": 0,
                  "desc": "",
                  "host": "",
                  "link": "https://www.wanandroid.com/blog/show/3741",
                  "tags": [],
                  "type": 0,
                  "audit": 1,
                  "fresh": false,
                  "title": "Android 技术周刊 （2025-01-28 ~ 2025-02-08）",
                  "author": "张鸿洋",
                  "descMd": "",
                  "origin": "",
                  "prefix": "",
                  "userId": -1,
                  "apkLink": "",
                  "canEdit": false,
                  "collect": false,
                  "visible": 1,
                  "adminAdd": false,
                  "courseId": 13,
                  "niceDate": "2025-02-08 00:00",
                  "chapterId": 543,
                  "shareDate": 1738944600000,
                  "shareUser": "",
                  "isAdminAdd": false,
                  "chapterName": "Android技术周报",
                  "envelopePic": "",
                  "projectLink": "",
                  "publishTime": 1738944000000,
                  "selfVisible": 0,
                  "niceShareDate": "2025-02-08 00:10",
                  "superChapterId": 543,
                  "superChapterName": "技术周报",
                  "realSuperChapterId": 542
                }
              ],
              "total": 15969,
              "offset": 0,
              "curPage": 1,
              "pageCount": 799
            },
            "errorMsg": "",
            "errorCode": 0
          },
          "text": "{\"data\":{\"curPage\":1,\"datas\":[{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":true,\"host\":\"\",\"id\":29628,\"isAdminAdd\":false,\"link\":\"https://juejin.cn/post/7478994020612374543\",\"niceDate\":\"21分钟前\",\"niceShareDate\":\"21分钟前\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1741582098000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1741582098000,\"shareUser\":\"wgllss\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"该怎么学Android进阶，拒绝沦为高级三方SDK调用工程师？\",\"type\":0,\"userId\":161755,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":true,\"host\":\"\",\"id\":29627,\"isAdminAdd\":false,\"link\":\"https://blog.csdn.net/qq_40533422/article/details/146093982\",\"niceDate\":\"4小时前\",\"niceShareDate\":\"4小时前\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1741567871000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1741567871000,\"shareUser\":\"JasonYin\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"Android 仿 DeepSeek 思考效果：逐字显示 AI 生成内容，支持加粗、颜色，复制内容\",\"type\":0,\"userId\":9296,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"张鸿洋\",\"canEdit\":false,\"chapterId\":543,\"chapterName\":\"Android技术周报\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29606,\"isAdminAdd\":false,\"link\":\"https://www.wanandroid.com/blog/show/3750\",\"niceDate\":\"2天前\",\"niceShareDate\":\"2天前\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1741363200000,\"realSuperChapterId\":542,\"selfVisible\":0,\"shareDate\":1741363800000,\"shareUser\":\"\",\"superChapterId\":543,\"superChapterName\":\"技术周报\",\"tags\":[],\"title\":\"Android 技术周刊 （2025-03-01 ~ 2025-03-08）\",\"type\":0,\"userId\":-1,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29605,\"isAdminAdd\":false,\"link\":\"https://blog.csdn.net/u013290250/article/details/145769573\",\"niceDate\":\"2天前\",\"niceShareDate\":\"2天前\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1741326281000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1741326281000,\"shareUser\":\"duangduang\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"Flutter&mdash;&mdash;更详细原生交互（MethodChannel、EventChannel、BasicMessageChannel）使用教程\",\"type\":0,\"userId\":149113,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29604,\"isAdminAdd\":false,\"link\":\"https://mp.weixin.qq.com/s/b6d2vupUG0TtM0l-jsgIHQ\",\"niceDate\":\"2025-03-07 12:29\",\"niceShareDate\":\"2025-03-07 12:29\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1741321786000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1741321786000,\"shareUser\":\"残页\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"Android分屏功能原理（基于Android12L）\",\"type\":0,\"userId\":12467,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29510,\"isAdminAdd\":false,\"link\":\"https://juejin.cn/post/7469809220646010916\",\"niceDate\":\"2025-03-02 11:14\",\"niceShareDate\":\"2025-03-01 22:36\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1740885244000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1740839799000,\"shareUser\":\"鸿洋\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"记一次无障碍测试引发app崩溃问题的排查与解决在APP发版前，我们一般都会先跑mtc的自动化测试框架，也就是让脚本模拟用\",\"type\":0,\"userId\":2,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"张鸿洋\",\"canEdit\":false,\"chapterId\":543,\"chapterName\":\"Android技术周报\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29508,\"isAdminAdd\":false,\"link\":\"https://www.wanandroid.com/blog/show/3747\",\"niceDate\":\"2025-03-01 00:00\",\"niceShareDate\":\"2025-03-01 00:10\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1740758400000,\"realSuperChapterId\":542,\"selfVisible\":0,\"shareDate\":1740759000000,\"shareUser\":\"\",\"superChapterId\":543,\"superChapterName\":\"技术周报\",\"tags\":[],\"title\":\"Android 技术周刊 （2025-02-22 ~ 2025-03-01）\",\"type\":0,\"userId\":-1,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29506,\"isAdminAdd\":false,\"link\":\"https://juejin.cn/post/7475575836705898533\",\"niceDate\":\"2025-02-27 09:00\",\"niceShareDate\":\"2025-02-27 09:00\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1740618053000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1740618053000,\"shareUser\":\"wgllss\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"2025年Android六边形战士开发趋势，需要掌握哪些技能可自我反省\",\"type\":0,\"userId\":161755,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"张鸿洋\",\"canEdit\":false,\"chapterId\":543,\"chapterName\":\"Android技术周报\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29494,\"isAdminAdd\":false,\"link\":\"https://www.wanandroid.com/blog/show/3745\",\"niceDate\":\"2025-02-22 00:00\",\"niceShareDate\":\"2025-02-22 00:10\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1740153600000,\"realSuperChapterId\":542,\"selfVisible\":0,\"shareDate\":1740154200000,\"shareUser\":\"\",\"superChapterId\":543,\"superChapterName\":\"技术周报\",\"tags\":[],\"title\":\"Android 技术周刊 （2025-02-15 ~ 2025-02-22）\",\"type\":0,\"userId\":-1,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29493,\"isAdminAdd\":false,\"link\":\"https://juejin.cn/post/7471630643534512164\",\"niceDate\":\"2025-02-21 17:43\",\"niceShareDate\":\"2025-02-21 17:43\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1740131039000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1740131039000,\"shareUser\":\"ldlywt\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"我写了个App，上架 Google Play 一年，下载不到 10 次，于是决定把它开源了\",\"type\":0,\"userId\":2470,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29492,\"isAdminAdd\":false,\"link\":\"https://www.bilibili.com/video/BV1bs421N7tR/?spm_id_from=888.80997.embed_other.whitelist&amp;t=15.406298&amp;bvid=BV1bs421N7tR&amp;vd_source=f43def12c6eccac37abb1f5d026db37a\",\"niceDate\":\"2025-02-20 21:43\",\"niceShareDate\":\"2025-02-20 21:43\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1740058980000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1740058980000,\"shareUser\":\"鸿洋\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"通往AGI之路分享：AI Agent-Coze搭建 5月8日\",\"type\":0,\"userId\":2,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29490,\"isAdminAdd\":false,\"link\":\"https://juejin.cn/post/7472223022192836659\",\"niceDate\":\"2025-02-17 17:44\",\"niceShareDate\":\"2025-02-17 17:44\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1739785477000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1739785477000,\"shareUser\":\"wgllss\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"Android拦截其它播放声音：内录音，外录音，录屏，剪辑，混音，一键制作大片全搞定\",\"type\":0,\"userId\":161755,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"张鸿洋\",\"canEdit\":false,\"chapterId\":543,\"chapterName\":\"Android技术周报\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29488,\"isAdminAdd\":false,\"link\":\"https://www.wanandroid.com/blog/show/3743\",\"niceDate\":\"2025-02-15 00:00\",\"niceShareDate\":\"2025-02-15 00:10\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1739548800000,\"realSuperChapterId\":542,\"selfVisible\":0,\"shareDate\":1739549400000,\"shareUser\":\"\",\"superChapterId\":543,\"superChapterName\":\"技术周报\",\"tags\":[],\"title\":\"Android 技术周刊 （2025-02-08 ~ 2025-02-15）\",\"type\":0,\"userId\":-1,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29487,\"isAdminAdd\":false,\"link\":\"https://juejin.cn/post/7469991575277207602\",\"niceDate\":\"2025-02-13 20:56\",\"niceShareDate\":\"2025-02-13 20:56\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1739451373000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1739451373000,\"shareUser\":\"wgllss\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"元宵节前福利，神之操作，一键下载想要的同类型多个图片？？\",\"type\":0,\"userId\":161755,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29480,\"isAdminAdd\":false,\"link\":\"https://zhuanlan.zhihu.com/p/708244292\",\"niceDate\":\"2025-02-10 11:55\",\"niceShareDate\":\"2025-02-10 11:55\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1739159721000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1739159716000,\"shareUser\":\"残页\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"鸿蒙内核论文阅读\",\"type\":0,\"userId\":12467,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29479,\"isAdminAdd\":false,\"link\":\"https://blog.csdn.net/qq_40533422/article/details/144839240\",\"niceDate\":\"2025-02-10 08:45\",\"niceShareDate\":\"2025-02-10 08:45\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1739148322000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1739148322000,\"shareUser\":\"JasonYin\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"HarmonyOSNEXT实战:搭建模块化项目架构，附完整代码仓\",\"type\":0,\"userId\":9296,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"鸿洋\",\"canEdit\":false,\"chapterId\":408,\"chapterName\":\"鸿洋\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29484,\"isAdminAdd\":false,\"link\":\"https://mp.weixin.qq.com/s/_zlJeB1xYm7grr9w8WSsfA\",\"niceDate\":\"2025-02-10 00:00\",\"niceShareDate\":\"2025-02-10 16:30\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1739116800000,\"realSuperChapterId\":407,\"selfVisible\":0,\"shareDate\":1739176247000,\"shareUser\":\"\",\"superChapterId\":408,\"superChapterName\":\"公众号\",\"tags\":[{\"name\":\"公众号\",\"url\":\"/wxarticle/list/408/1\"}],\"title\":\"再学安卓 - binder之Framework通信流程\",\"type\":0,\"userId\":-1,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"\",\"canEdit\":false,\"chapterId\":502,\"chapterName\":\"自助\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29476,\"isAdminAdd\":false,\"link\":\"https://juejin.cn/post/7468865451134091275\",\"niceDate\":\"2025-02-08 15:47\",\"niceShareDate\":\"2025-02-08 15:47\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1739000821000,\"realSuperChapterId\":493,\"selfVisible\":0,\"shareDate\":1739000821000,\"shareUser\":\"wgllss\",\"superChapterId\":494,\"superChapterName\":\"广场Tab\",\"tags\":[],\"title\":\"Android之等级金字塔之Compose智能实现\",\"type\":0,\"userId\":161755,\"visible\":1,\"zan\":0},{\"adminAdd\":false,\"apkLink\":\"\",\"audit\":1,\"author\":\"张鸿洋\",\"canEdit\":false,\"chapterId\":543,\"chapterName\":\"Android技术周报\",\"collect\":false,\"courseId\":13,\"desc\":\"\",\"descMd\":\"\",\"envelopePic\":\"\",\"fresh\":false,\"host\":\"\",\"id\":29474,\"isAdminAdd\":false,\"link\":\"https://www.wanandroid.com/blog/show/3741\",\"niceDate\":\"2025-02-08 00:00\",\"niceShareDate\":\"2025-02-08 00:10\",\"origin\":\"\",\"prefix\":\"\",\"projectLink\":\"\",\"publishTime\":1738944000000,\"realSuperChapterId\":542,\"selfVisible\":0,\"shareDate\":1738944600000,\"shareUser\":\"\",\"superChapterId\":543,\"superChapterName\":\"技术周报\",\"tags\":[],\"title\":\"Android 技术周刊 （2025-01-28 ~ 2025-02-08）\",\"type\":0,\"userId\":-1,\"visible\":1,\"zan\":0}],\"offset\":0,\"over\":false,\"pageCount\":799,\"size\":20,\"total\":15969},\"errorCode\":0,\"errorMsg\":\"\"}",
          "time": 0.24893593788146973,
          "headers": {
            "Date": "Mon, 10 Mar 2025 05:09:49 GMT",
            "Server": "Apache-Coyote/1.1",
            "Expires": "Thu, 01 Jan 1970 08:00:00 CST",
            "Content-Type": "application/json;charset=UTF-8",
            "Cache-Control": "private",
            "Transfer-Encoding": "chunked"
          }
        },
        "cache_data": {
          "cookie": "JSESSIONID=71D8A4BB60E34325A00B0D178C05C765; Path=/; Secure; HttpOnly, loginUserName=mango_test; Expires=Wed, 09-Apr-2025 05:09:49 GMT; Path=/, token_pass=5d9b90bcb70640183e09d1e755ead823; Expires=Wed, 09-Apr-2025 05:09:49 GMT; Path=/, loginUserName_wanandroid_com=mango_test; Domain=wanandroid.com; Expires=Wed, 09-Apr-2025 05:09:49 GMT; Path=/, token_pass_wanandroid_com=5d9b90bcb70640183e09d1e755ead823; Domain=wanandroid.com; Expires=Wed, 09-Apr-2025 05:09:49 GMT; Path=/",
          "密码A": "123456",
          "账号A": "mango_test"
        },
        "api_info_id": 2,
        "error_message": null
      }
    ],
    "retry": 1,
    "push_time": "2025-03-10T13:09:48.533411"
  },
  {
    "id": 80,
    "create_time": "2025-03-09 22:23:11",
    "update_time": "2025-03-10 13:09:50",
    "project_product": {
      "id": 2,
      "create_time": "2024-11-24 19:58:25",
      "update_time": "2024-11-26 21:24:46",
      "project": {
        "id": 1,
        "create_time": "2024-11-24 00:38:16",
        "update_time": "2024-11-24 00:38:22",
        "name": "演示DEMO",
        "status": 1
      },
      "name": "玩安卓",
      "ui_client_type": 0,
      "api_client_type": 0
    },
    "test_suite": {
      "id": 232853768174,
      "create_time": "2025-03-09 22:23:11",
      "update_time": "2025-03-11 10:49:36",
      "test_env": 2,
      "status": 3,
      "is_notice": 0,
      "project_product": 2,
      "user": 1,
      "tasks": 9
    },
    "type": 2,
    "test_env": 2,
    "case_id": 13,
    "case_name": "API登录",
    "status": 1,
    "error_message": null,
    "result_data": [
      {
        "name": "正确的账号，正确的密码，进行登录",
        "stop": 1741583390410,
        "uuid": "6c73ba76-5643-422c-b7b6-6c27f51e3073",
        "start": 1741583389706,
        "labels": [
          {
            "name": "epic",
            "value": "演示-API自动化-常规API-玩安卓"
          },
          {
            "name": "feature",
            "value": "登录模块"
          },
          {
            "name": "tag",
            "value": "flaky(reruns=3)"
          },
          {
            "name": "parentSuite",
            "value": "mango_pytest.auto_test.api_wan_android.test_case.test_login"
          },
          {
            "name": "suite",
            "value": "test_login"
          },
          {
            "name": "subSuite",
            "value": "TestLogin"
          },
          {
            "name": "host",
            "value": "c36909d3cf36"
          },
          {
            "name": "thread",
            "value": "9-ThreadPoolExecutor-2_0"
          },
          {
            "name": "framework",
            "value": "pytest"
          },
          {
            "name": "language",
            "value": "cpython3"
          },
          {
            "name": "package",
            "value": "mango_pytest.auto_test.api_wan_android.test_case.test_login.test_login"
          }
        ],
        "status": 1,
        "fullName": "mango_pytest.auto_test.api_wan_android.test_case.test_login.test_login.TestLogin#test_01",
        "historyId": "003a46c81d4f6e00e933b63a8771a88a",
        "parameters": [
          {
            "name": "test_case",
            "value": "{'id': 1, 'project_name': '玩安卓', '模块': '登录', 'name': '正确的账号，正确的密码，进行登录', 'params': None, 'data': '{\"username\": \"maopeng\", \"password\": \"729164035\"}', 'json': None, 'file': None, 'other_data': None, 'ass_response_whole': None, 'ass_response_value': None, 'ass_sql': None, 'front_sql': None, 'posterior_sql': None, 'posterior_response': None, 'dump_data': None}"
          }
        ],
        "testCaseId": "85aa4dc7955f514fbe12b6dcf8c51b30",
        "attachments": [
          {
            "name": "用例数据",
            "source": "{\"id\":1,\"project_name\":\"玩安卓\",\"name\":\"正确的账号，正确的密码，进行登录\",\"params\":null,\"data\":{\"username\":\"maopeng\",\"password\":\"729164035\"},\"json_data\":null,\"file\":null,\"other_data\":null,\"ass_response_whole\":null,\"ass_response_value\":null,\"ass_sql\":null,\"front_sql\":null,\"posterior_sql\":null,\"posterior_response\":null,\"dump_data\":null}"
          },
          {
            "name": "URL",
            "source": "https://wanandroid.com/user/login"
          },
          {
            "name": "请求方法",
            "source": "POST"
          },
          {
            "name": "请求头",
            "source": "{'Content-Type': 'application/x-www-form-urlencoded'}"
          },
          {
            "name": "表单",
            "source": "{\"username\": \"maopeng\", \"password\": \"729164035\"}"
          },
          {
            "name": "响应状态码",
            "source": "200"
          },
          {
            "name": "响应时间（毫秒）",
            "source": "700.3159523010254"
          },
          {
            "name": "响应结果",
            "source": "{\"data\":{\"admin\":false,\"chapterTops\":[],\"coinCount\":3695,\"collectIds\":[29326],\"email\":\"\",\"icon\":\"\",\"id\":158877,\"nickname\":\"maopeng\",\"password\":\"\",\"publicName\":\"maopeng\",\"token\":\"\",\"type\":0,\"username\":\"maopeng\"},\"errorCode\":0,\"errorMsg\":\"\"}"
          },
          {
            "name": "log",
            "type": "text/plain",
            "source": "INFO     /app/mango_pytest/logs\\info-log.log:__init__.py:38 \n========================================================================================================================================================================================================\n用例标题: 正确的账号，正确的密码，进行登录\n请求路径: https://wanandroid.com/user/login\n请求方式: POST\n请 求 头:  {'Content-Type': 'application/x-www-form-urlencoded'}\n请求data：{'username': 'maopeng', 'password': '729164035'}\nHttp状态码: 200\n接口响应时长: 0.7003159523010254 ms\n接口响应内容: {\"data\":{\"admin\":false,\"chapterTops\":[],\"coinCount\":3695,\"collectIds\":[29326],\"email\":\"\",\"icon\":\"\",\"id\":158877,\"nickname\":\"maopeng\",\"password\":\"\",\"publicName\":\"maopeng\",\"token\":\"\",\"type\":0,\"username\":\"maopeng\"},\"errorCode\":0,\"errorMsg\":\"\"}\n========================================================================================================================================================================================================"
          },
          {
            "name": "stderr",
            "type": "text/plain",
            "source": "--- Logging error ---\nTraceback (most recent call last):\n  File \"/usr/local/lib/python3.10/logging/__init__.py\", line 1103, in emit\n    stream.write(msg + self.terminator)\nValueError: I/O operation on closed file.\nCall stack:\n  File \"/usr/local/lib/python3.10/threading.py\", line 973, in _bootstrap\n    self._bootstrap_inner()\n  File \"/usr/local/lib/python3.10/threading.py\", line 1016, in _bootstrap_inner\n    self.run()\n  File \"/usr/local/lib/python3.10/threading.py\", line 953, in run\n    self._target(*self._args, **self._kwargs)\n  File \"/usr/local/lib/python3.10/concurrent/futures/thread.py\", line 83, in _worker\n    work_item.run()\n  File \"/usr/local/lib/python3.10/concurrent/futures/thread.py\", line 58, in run\n    result = self.fn(*self.args, **self.kwargs)\n  File \"/app/src/auto_test/auto_pytest/service/test_case/case_flow.py\", line 51, in execute_task\n    return test_case.test_case_main(case_model.case_id)\n  File \"/app/src/auto_test/auto_pytest/service/test_case/test_case.py\", line 40, in test_case_main\n    pytest.main(pytest_args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/config/__init__.py\", line 175, in main\n    ret: ExitCode | int = config.hook.pytest_cmdline_main(config=config)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 330, in pytest_cmdline_main\n    return wrap_session(config, _main)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 283, in wrap_session\n    session.exitstatus = doit(config, session) or 0\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 337, in _main\n    config.hook.pytest_runtestloop(session=session)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 362, in pytest_runtestloop\n    item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/pytest_rerunfailures.py\", line 549, in pytest_runtest_protocol\n    reports = runtestprotocol(item, nextitem=nextitem, log=False)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 132, in runtestprotocol\n    reports.append(call_and_report(item, \"call\", log))\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 241, in call_and_report\n    call = CallInfo.from_call(\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 341, in from_call\n    result: TResult | None = func()\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 242, in <lambda>\n    lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 174, in pytest_runtest_call\n    item.runtest()\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/python.py\", line 1627, in runtest\n    self.ihook.pytest_pyfunc_call(pyfuncitem=self)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/python.py\", line 159, in pytest_pyfunc_call\n    result = testfunction(**testargs)\n  File \"/app/mango_pytest/tools/decorator/response.py\", line 44, in wrapper\n    func(self, data=data)\n  File \"/app/mango_pytest/auto_test/api_wan_android/test_case/test_login/test_login.py\", line 24, in test_01\n    data = self.api_login(data)\n  File \"/app/mango_pytest/tools/decorator/response.py\", line 74, in wrapper\n    res_args = func(self, data)\n  File \"/app/mango_pytest/auto_test/api_wan_android/act/login/login.py\", line 22, in api_login\n    return self.http(data)\n  File \"/app/mango_pytest/tools/decorator/response.py\", line 156, in swapper\n    log.info(_log_msg)\n  File \"/usr/local/lib/python3.10/site-packages/mangokit/tools/log_collector/__init__.py\", line 48, in info\n    self._log('info', msg)\n  File \"/usr/local/lib/python3.10/site-packages/mangokit/tools/log_collector/__init__.py\", line 38, in _log\n    log_file.log(self.DEBUG.level_relations[level], str(msg))\nMessage: '\\n========================================================================================================================================================================================================\\n用例标题: 正确的账号，正确的密码，进行登录\\n请求路径: https://wanandroid.com/user/login\\n请求方式: POST\\n请 求 头:  {\\'Content-Type\\': \\'application/x-www-form-urlencoded\\'}\\n请求data：{\\'username\\': \\'maopeng\\', \\'password\\': \\'729164035\\'}\\nHttp状态码: 200\\n接口响应时长: 0.7003159523010254 ms\\n接口响应内容: {\"data\":{\"admin\":false,\"chapterTops\":[],\"coinCount\":3695,\"collectIds\":[29326],\"email\":\"\",\"icon\":\"\",\"id\":158877,\"nickname\":\"maopeng\",\"password\":\"\",\"publicName\":\"maopeng\",\"token\":\"\",\"type\":0,\"username\":\"maopeng\"},\"errorCode\":0,\"errorMsg\":\"\"}\\n========================================================================================================================================================================================================'\nArguments: ()\n"
          }
        ]
      },
      {
        "name": "错误的账号，错误的密码，进行登录",
        "stop": 1741583390886,
        "uuid": "ecca0a46-1fc6-4922-8abf-4b1ef17d74dd",
        "start": 1741583390639,
        "labels": [
          {
            "name": "epic",
            "value": "演示-API自动化-常规API-玩安卓"
          },
          {
            "name": "feature",
            "value": "登录模块"
          },
          {
            "name": "tag",
            "value": "flaky(reruns=3)"
          },
          {
            "name": "parentSuite",
            "value": "mango_pytest.auto_test.api_wan_android.test_case.test_login"
          },
          {
            "name": "suite",
            "value": "test_login"
          },
          {
            "name": "subSuite",
            "value": "TestLogin"
          },
          {
            "name": "host",
            "value": "c36909d3cf36"
          },
          {
            "name": "thread",
            "value": "9-ThreadPoolExecutor-2_0"
          },
          {
            "name": "framework",
            "value": "pytest"
          },
          {
            "name": "language",
            "value": "cpython3"
          },
          {
            "name": "package",
            "value": "mango_pytest.auto_test.api_wan_android.test_case.test_login.test_login"
          }
        ],
        "status": 1,
        "fullName": "mango_pytest.auto_test.api_wan_android.test_case.test_login.test_login.TestLogin#test_03",
        "historyId": "df72eef91fa9adc97de5249740d2be98",
        "parameters": [
          {
            "name": "test_case",
            "value": "{'id': 3, 'project_name': '玩安卓', '模块': '登录', 'name': '错误的账号，错误的密码，进行登录', 'params': None, 'data': '{\"username\": \"maopeng1\", \"password\": \"7291640351\"}', 'json': None, 'file': None, 'other_data': None, 'ass_response_whole': None, 'ass_response_value': None, 'ass_sql': None, 'front_sql': None, 'posterior_sql': None, 'posterior_response': None, 'dump_data': None}"
          }
        ],
        "testCaseId": "a9509164c17b87e2cc982e47958a41db",
        "attachments": [
          {
            "name": "用例数据",
            "source": "{\"id\":3,\"project_name\":\"玩安卓\",\"name\":\"错误的账号，错误的密码，进行登录\",\"params\":null,\"data\":{\"username\":\"maopeng1\",\"password\":\"7291640351\"},\"json_data\":null,\"file\":null,\"other_data\":null,\"ass_response_whole\":null,\"ass_response_value\":null,\"ass_sql\":null,\"front_sql\":null,\"posterior_sql\":null,\"posterior_response\":null,\"dump_data\":null}"
          },
          {
            "name": "URL",
            "source": "https://wanandroid.com/user/login"
          },
          {
            "name": "请求方法",
            "source": "POST"
          },
          {
            "name": "请求头",
            "source": "{'Content-Type': 'application/x-www-form-urlencoded'}"
          },
          {
            "name": "表单",
            "source": "{\"username\": \"maopeng1\", \"password\": \"7291640351\"}"
          },
          {
            "name": "响应状态码",
            "source": "200"
          },
          {
            "name": "响应时间（毫秒）",
            "source": "243.87216567993164"
          },
          {
            "name": "响应结果",
            "source": "{\"data\":null,\"errorCode\":-1,\"errorMsg\":\"账号密码不匹配！\"}"
          },
          {
            "name": "log",
            "type": "text/plain",
            "source": "INFO     /app/mango_pytest/logs\\info-log.log:__init__.py:38 \n========================================================================================================================================================================================================\n用例标题: 错误的账号，错误的密码，进行登录\n请求路径: https://wanandroid.com/user/login\n请求方式: POST\n请 求 头:  {'Content-Type': 'application/x-www-form-urlencoded'}\n请求data：{'username': 'maopeng1', 'password': '7291640351'}\nHttp状态码: 200\n接口响应时长: 0.24387216567993164 ms\n接口响应内容: {\"data\":null,\"errorCode\":-1,\"errorMsg\":\"账号密码不匹配！\"}\n========================================================================================================================================================================================================"
          },
          {
            "name": "stderr",
            "type": "text/plain",
            "source": "--- Logging error ---\nTraceback (most recent call last):\n  File \"/usr/local/lib/python3.10/logging/__init__.py\", line 1103, in emit\n    stream.write(msg + self.terminator)\nValueError: I/O operation on closed file.\nCall stack:\n  File \"/usr/local/lib/python3.10/threading.py\", line 973, in _bootstrap\n    self._bootstrap_inner()\n  File \"/usr/local/lib/python3.10/threading.py\", line 1016, in _bootstrap_inner\n    self.run()\n  File \"/usr/local/lib/python3.10/threading.py\", line 953, in run\n    self._target(*self._args, **self._kwargs)\n  File \"/usr/local/lib/python3.10/concurrent/futures/thread.py\", line 83, in _worker\n    work_item.run()\n  File \"/usr/local/lib/python3.10/concurrent/futures/thread.py\", line 58, in run\n    result = self.fn(*self.args, **self.kwargs)\n  File \"/app/src/auto_test/auto_pytest/service/test_case/case_flow.py\", line 51, in execute_task\n    return test_case.test_case_main(case_model.case_id)\n  File \"/app/src/auto_test/auto_pytest/service/test_case/test_case.py\", line 40, in test_case_main\n    pytest.main(pytest_args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/config/__init__.py\", line 175, in main\n    ret: ExitCode | int = config.hook.pytest_cmdline_main(config=config)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 330, in pytest_cmdline_main\n    return wrap_session(config, _main)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 283, in wrap_session\n    session.exitstatus = doit(config, session) or 0\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 337, in _main\n    config.hook.pytest_runtestloop(session=session)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 362, in pytest_runtestloop\n    item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/pytest_rerunfailures.py\", line 549, in pytest_runtest_protocol\n    reports = runtestprotocol(item, nextitem=nextitem, log=False)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 132, in runtestprotocol\n    reports.append(call_and_report(item, \"call\", log))\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 241, in call_and_report\n    call = CallInfo.from_call(\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 341, in from_call\n    result: TResult | None = func()\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 242, in <lambda>\n    lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 174, in pytest_runtest_call\n    item.runtest()\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/python.py\", line 1627, in runtest\n    self.ihook.pytest_pyfunc_call(pyfuncitem=self)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/python.py\", line 159, in pytest_pyfunc_call\n    result = testfunction(**testargs)\n  File \"/app/mango_pytest/tools/decorator/response.py\", line 44, in wrapper\n    func(self, data=data)\n  File \"/app/mango_pytest/auto_test/api_wan_android/test_case/test_login/test_login.py\", line 40, in test_03\n    data = self.api_login(data)\n  File \"/app/mango_pytest/tools/decorator/response.py\", line 74, in wrapper\n    res_args = func(self, data)\n  File \"/app/mango_pytest/auto_test/api_wan_android/act/login/login.py\", line 22, in api_login\n    return self.http(data)\n  File \"/app/mango_pytest/tools/decorator/response.py\", line 156, in swapper\n    log.info(_log_msg)\n  File \"/usr/local/lib/python3.10/site-packages/mangokit/tools/log_collector/__init__.py\", line 48, in info\n    self._log('info', msg)\n  File \"/usr/local/lib/python3.10/site-packages/mangokit/tools/log_collector/__init__.py\", line 38, in _log\n    log_file.log(self.DEBUG.level_relations[level], str(msg))\nMessage: '\\n========================================================================================================================================================================================================\\n用例标题: 错误的账号，错误的密码，进行登录\\n请求路径: https://wanandroid.com/user/login\\n请求方式: POST\\n请 求 头:  {\\'Content-Type\\': \\'application/x-www-form-urlencoded\\'}\\n请求data：{\\'username\\': \\'maopeng1\\', \\'password\\': \\'7291640351\\'}\\nHttp状态码: 200\\n接口响应时长: 0.24387216567993164 ms\\n接口响应内容: {\"data\":null,\"errorCode\":-1,\"errorMsg\":\"账号密码不匹配！\"}\\n========================================================================================================================================================================================================'\nArguments: ()\n"
          }
        ]
      },
      {
        "name": "正确的账号，错误的密码，进行登录",
        "stop": 1741583390636,
        "uuid": "2ad9e068-040c-4490-a519-94f333dff636",
        "start": 1741583390413,
        "steps": [
          {
            "name": "检查错误消息",
            "stop": 1741583390636,
            "start": 1741583390636,
            "status": "passed",
            "attachments": [
              {
                "name": "Expected Error Message",
                "type": "text/plain",
                "source": "0a1d90aa-eed5-48b1-8676-8cdb36d54e35-attachment.txt"
              },
              {
                "name": "Actual Error Message",
                "type": "text/plain",
                "source": "8081398d-06ec-4c25-80d6-9200fbea968b-attachment.txt"
              }
            ]
          }
        ],
        "labels": [
          {
            "name": "epic",
            "value": "演示-API自动化-常规API-玩安卓"
          },
          {
            "name": "feature",
            "value": "登录模块"
          },
          {
            "name": "tag",
            "value": "flaky(reruns=3)"
          },
          {
            "name": "parentSuite",
            "value": "mango_pytest.auto_test.api_wan_android.test_case.test_login"
          },
          {
            "name": "suite",
            "value": "test_login"
          },
          {
            "name": "subSuite",
            "value": "TestLogin"
          },
          {
            "name": "host",
            "value": "c36909d3cf36"
          },
          {
            "name": "thread",
            "value": "9-ThreadPoolExecutor-2_0"
          },
          {
            "name": "framework",
            "value": "pytest"
          },
          {
            "name": "language",
            "value": "cpython3"
          },
          {
            "name": "package",
            "value": "mango_pytest.auto_test.api_wan_android.test_case.test_login.test_login"
          }
        ],
        "status": 1,
        "fullName": "mango_pytest.auto_test.api_wan_android.test_case.test_login.test_login.TestLogin#test_02",
        "historyId": "d52ae98f055caa4fe617fb4bcbb1eab4",
        "parameters": [
          {
            "name": "test_case",
            "value": "{'id': 2, 'project_name': '玩安卓', '模块': '登录', 'name': '正确的账号，错误的密码，进行登录', 'params': None, 'data': '{\"username\": \"maopeng\", \"password\": \"7291640351\"}', 'json': None, 'file': None, 'other_data': None, 'ass_response_whole': None, 'ass_response_value': None, 'ass_sql': None, 'front_sql': None, 'posterior_sql': None, 'posterior_response': None, 'dump_data': None}"
          }
        ],
        "testCaseId": "ff83c427bfc6e883411ed33496463f7f",
        "attachments": [
          {
            "name": "用例数据",
            "source": "{\"id\":2,\"project_name\":\"玩安卓\",\"name\":\"正确的账号，错误的密码，进行登录\",\"params\":null,\"data\":{\"username\":\"maopeng\",\"password\":\"7291640351\"},\"json_data\":null,\"file\":null,\"other_data\":null,\"ass_response_whole\":null,\"ass_response_value\":null,\"ass_sql\":null,\"front_sql\":null,\"posterior_sql\":null,\"posterior_response\":null,\"dump_data\":null}"
          },
          {
            "name": "URL",
            "source": "https://wanandroid.com/user/login"
          },
          {
            "name": "请求方法",
            "source": "POST"
          },
          {
            "name": "请求头",
            "source": "{'Content-Type': 'application/x-www-form-urlencoded'}"
          },
          {
            "name": "表单",
            "source": "{\"username\": \"maopeng\", \"password\": \"7291640351\"}"
          },
          {
            "name": "响应状态码",
            "source": "200"
          },
          {
            "name": "响应时间（毫秒）",
            "source": "220.048189163208"
          },
          {
            "name": "响应结果",
            "source": "{\"data\":null,\"errorCode\":-1,\"errorMsg\":\"账号密码不匹配！\"}"
          },
          {
            "name": "log",
            "type": "text/plain",
            "source": "INFO     /app/mango_pytest/logs\\info-log.log:__init__.py:38 \n========================================================================================================================================================================================================\n用例标题: 正确的账号，错误的密码，进行登录\n请求路径: https://wanandroid.com/user/login\n请求方式: POST\n请 求 头:  {'Content-Type': 'application/x-www-form-urlencoded'}\n请求data：{'username': 'maopeng', 'password': '7291640351'}\nHttp状态码: 200\n接口响应时长: 0.220048189163208 ms\n接口响应内容: {\"data\":null,\"errorCode\":-1,\"errorMsg\":\"账号密码不匹配！\"}\n========================================================================================================================================================================================================"
          },
          {
            "name": "stderr",
            "type": "text/plain",
            "source": "--- Logging error ---\nTraceback (most recent call last):\n  File \"/usr/local/lib/python3.10/logging/__init__.py\", line 1103, in emit\n    stream.write(msg + self.terminator)\nValueError: I/O operation on closed file.\nCall stack:\n  File \"/usr/local/lib/python3.10/threading.py\", line 973, in _bootstrap\n    self._bootstrap_inner()\n  File \"/usr/local/lib/python3.10/threading.py\", line 1016, in _bootstrap_inner\n    self.run()\n  File \"/usr/local/lib/python3.10/threading.py\", line 953, in run\n    self._target(*self._args, **self._kwargs)\n  File \"/usr/local/lib/python3.10/concurrent/futures/thread.py\", line 83, in _worker\n    work_item.run()\n  File \"/usr/local/lib/python3.10/concurrent/futures/thread.py\", line 58, in run\n    result = self.fn(*self.args, **self.kwargs)\n  File \"/app/src/auto_test/auto_pytest/service/test_case/case_flow.py\", line 51, in execute_task\n    return test_case.test_case_main(case_model.case_id)\n  File \"/app/src/auto_test/auto_pytest/service/test_case/test_case.py\", line 40, in test_case_main\n    pytest.main(pytest_args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/config/__init__.py\", line 175, in main\n    ret: ExitCode | int = config.hook.pytest_cmdline_main(config=config)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 330, in pytest_cmdline_main\n    return wrap_session(config, _main)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 283, in wrap_session\n    session.exitstatus = doit(config, session) or 0\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 337, in _main\n    config.hook.pytest_runtestloop(session=session)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/main.py\", line 362, in pytest_runtestloop\n    item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/pytest_rerunfailures.py\", line 549, in pytest_runtest_protocol\n    reports = runtestprotocol(item, nextitem=nextitem, log=False)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 132, in runtestprotocol\n    reports.append(call_and_report(item, \"call\", log))\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 241, in call_and_report\n    call = CallInfo.from_call(\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 341, in from_call\n    result: TResult | None = func()\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 242, in <lambda>\n    lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/runner.py\", line 174, in pytest_runtest_call\n    item.runtest()\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/python.py\", line 1627, in runtest\n    self.ihook.pytest_pyfunc_call(pyfuncitem=self)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_hooks.py\", line 513, in __call__\n    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_manager.py\", line 120, in _hookexec\n    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)\n  File \"/usr/local/lib/python3.10/site-packages/pluggy/_callers.py\", line 103, in _multicall\n    res = hook_impl.function(*args)\n  File \"/usr/local/lib/python3.10/site-packages/_pytest/python.py\", line 159, in pytest_pyfunc_call\n    result = testfunction(**testargs)\n  File \"/app/mango_pytest/tools/decorator/response.py\", line 44, in wrapper\n    func(self, data=data)\n  File \"/app/mango_pytest/auto_test/api_wan_android/test_case/test_login/test_login.py\", line 29, in test_02\n    data = self.api_login(data)\n  File \"/app/mango_pytest/tools/decorator/response.py\", line 74, in wrapper\n    res_args = func(self, data)\n  File \"/app/mango_pytest/auto_test/api_wan_android/act/login/login.py\", line 22, in api_login\n    return self.http(data)\n  File \"/app/mango_pytest/tools/decorator/response.py\", line 156, in swapper\n    log.info(_log_msg)\n  File \"/usr/local/lib/python3.10/site-packages/mangokit/tools/log_collector/__init__.py\", line 48, in info\n    self._log('info', msg)\n  File \"/usr/local/lib/python3.10/site-packages/mangokit/tools/log_collector/__init__.py\", line 38, in _log\n    log_file.log(self.DEBUG.level_relations[level], str(msg))\nMessage: '\\n========================================================================================================================================================================================================\\n用例标题: 正确的账号，错误的密码，进行登录\\n请求路径: https://wanandroid.com/user/login\\n请求方式: POST\\n请 求 头:  {\\'Content-Type\\': \\'application/x-www-form-urlencoded\\'}\\n请求data：{\\'username\\': \\'maopeng\\', \\'password\\': \\'7291640351\\'}\\nHttp状态码: 200\\n接口响应时长: 0.220048189163208 ms\\n接口响应内容: {\"data\":null,\"errorCode\":-1,\"errorMsg\":\"账号密码不匹配！\"}\\n========================================================================================================================================================================================================'\nArguments: ()\n"
          }
        ]
      }
    ],
    "retry": 1,
    "push_time": "2025-03-10T13:09:49.554270"
  }
])
</script>
