# # -*- coding: utf-8 -*-
# # @Project: auto_test
# # @Description:
# # @Time   : 2023/3/8 14:31
# # @Author : 毛鹏
# header-icon
# python想编写一个exe的文件，让windows电脑可以打开。请问python有什么比较好设计的框架，来管理我的代码
#
# header-icon
# 可以使用PyInstaller或者py2exe来将Python代码编译成Windows可执行文件（exe文件）。
# PyInstaller是一个轻量级的工具，它会将Python代码打包成一个独立的可执行文件，不需要Python解释器即可运行。使用PyInstaller可以方便地将Python代码打包成一个单一的exe文件，还可以为exe文件添加图标、版本信息等。
# py2exe是一个Python库，它可以将Python代码编译成Windows可执行文件。与PyInstaller相比，py2exe的功能更加丰富，可以支持多种Python版本、第三方库和模块。
# 使用这两个框架，你可以方便地将你的Python代码打包成一个exe文件，让Windows电脑上的用户可以直接运行你的应用程序。
#
# header-icon
# 有没有那种可以管理类的创建和销毁的，因为我打包的exe文件容易没反应
#
# header-icon
# 如果你的打包的exe文件容易没反应，可能是因为程序中存在内存泄漏或者资源泄漏等问题。你可以考虑使用Python的上下文管理器（context manager）来帮助你管理类的创建和销毁，以避免这些问题的发生。
# Python的上下文管理器是通过实现__enter__()和__exit__()方法来实现的。__enter__()方法在上下文管理器进入时被调用，__exit__()方法在上下文管理器离开时被调用。你可以在__enter__()方法中创建你的类实例，然后在__exit__()方法中销毁它。
# 下面是一个简单的使用上下文管理器来管理类的创建和销毁的例子：
#
# python
# Copy code
# class MyClass:
#     def __init__(self):
#         print('MyClass created')
#     def __del__(self):
#         print('MyClass destroyed')
# class MyClassManager:
#     def __init__(self):
#         print('MyClassManager created')
#     def __enter__(self):
#         self.obj = MyClass()
#         return self.obj
#     def __exit__(self, exc_type, exc_value, traceback):
#         self.obj.__del__()
#         print('MyClassManager destroyed')
# with MyClassManager() as obj:
#     print('Using MyClass object')
#
# 在这个例子中，MyClassManager是一个上下文管理器，它在__enter__()方法中创建了MyClass的实例，并返回该实例。在with语句块中，我们可以通过obj访问到MyClass的实例，进行需要的操作。在with语句块执行完毕后，__exit__()方法会被调用，销毁MyClass的实例，以及销毁MyClassManager的实例。
# 使用上下文管理器来管理类的创建和销毁，可以帮助你避免内存泄漏和资源泄漏等问题，同时提高程序的稳定性和性能。
#
# header-icon
# 我使用Playwright 实例化的对象，在exe中进行实例化，然后我强制关闭这个浏览器，要怎么彻底删除这个类。不让不影响后续流程
#
# header-icon
# 在Python中，你可以通过del语句来删除对象，释放对象占用的内存空间。在你强制关闭浏览器后，你可以通过del语句来删除Playwright实例化的对象，以释放对象占用的内存空间，避免影响后续流程。
# 例如：
#
# python
# Copy code
# from playwright.sync_api import Playwright, sync_playwright
# with sync_playwright() as playwright:
#     browser = playwright.chromium.launch(headless=False)
#     page = browser.new_page()
#     # do something with page
#     browser.close()
# del browser # 删除browser对象
# del page # 删除page对象
#
# 在上面的例子中，当你强制关闭浏览器后，你可以通过del语句来删除browser和page对象，以释放对象占用的内存空间。这样可以避免对象占用过多的内存空间，影响后续流程的执行。
#
# header-icon
# 那我要怎么让程序知道，浏览器已经被我强制关闭了呢？
#
# header-icon
# 在Python中，你可以通过try...except语句来捕获Playwright实例化的对象的异常，以判断浏览器是否已经被强制关闭了。
# 例如：
#
# python
# Copy code
# from playwright.sync_api import Playwright, sync_playwright
# with sync_playwright() as playwright:
#     try:
#         browser = playwright.chromium.launch(headless=False)
#         page = browser.new_page()
#         # do something with page
#         browser.close()
#     except Exception as e:
#         print('Browser closed unexpectedly:', e)
#     finally:
#         del browser # 删除browser对象
#         del page # 删除page对象
#
# 在上面的例子中，当你强制关闭浏览器后，browser.close()语句会抛出异常，触发except语句块中的代码执行。你可以在except语句块中打印异常信息，以便调试。然后在finally语句块中，你可以通过del语句来删除browser和page对象，以释放对象占用的内存空间。这样可以避免对象占用过多的内存空间，影响后续流程的执行。