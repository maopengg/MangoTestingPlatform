# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: PySide6 异步请求基类
# @Time   : 2026-03-09
# @Author : 毛鹏

import asyncio
from typing import Callable, Any, Optional
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QWidget


class AsyncResult:
    """异步请求结果"""
    def __init__(self, success: bool = True, data: Any = None, error: Exception = None):
        self.success = success
        self.data = data
        self.error = error


class AsyncRequestMixin:
    """
    PySide6 异步请求混入类
    
    使用方法：
    1. 继承此类和 QWidget
    2. 在 __init__ 中调用 self._init_async_request()
    3. 使用 self.async_request() 发起异步请求
    
    示例：
        class MyPage(QWidget, AsyncRequestMixin):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent
                self._init_async_request()
                
            def load_data(self):
                self.async_request(
                    self._fetch_data,
                    callback=self._on_result
                )
            
            async def _fetch_data(self):
                # 异步获取数据
                return await HTTP.user.info.get_userinfo(1)
            
            def _on_result(self, result: AsyncResult):
                # 在主线程中处理结果
                if result.success:
                    print(f"成功: {result.data}")
                else:
                    print(f"失败: {result.error}")
    """
    
    # 定义信号
    _async_result_signal = Signal(object)
    
    def _init_async_request(self):
        """初始化异步请求，必须在 __init__ 中调用"""
        if not hasattr(self, '_async_callbacks'):
            self._async_callbacks = {}
            self._async_result_signal.connect(self._handle_result)
    
    def async_request(
        self,
        async_func: Callable,
        callback: Optional[Callable[[AsyncResult], None]] = None,
        *args,
        **kwargs
    ):
        """
        发起异步请求
        
        Args:
            async_func: 异步函数
            callback: 结果回调（在主线程中执行），接收 AsyncResult 对象
            *args: 传递给异步函数的位置参数
            **kwargs: 传递给异步函数的关键字参数
        """
        # 获取事件循环
        loop = getattr(self, 'loop', None) or getattr(getattr(self, 'parent', None), 'loop', None)
        
        if not loop:
            raise RuntimeError("无法获取事件循环，请确保 parent 有 loop 属性")
        
        # 生成唯一ID
        request_id = id(async_func) + id(args) + id(kwargs)
        self._async_callbacks[request_id] = callback
        
        # 提交协程到事件循环
        asyncio.run_coroutine_threadsafe(
            self._execute_async(request_id, async_func, *args, **kwargs),
            loop
        )
    
    async def _execute_async(self, request_id: int, async_func: Callable, *args, **kwargs):
        """执行异步函数并处理结果"""
        try:
            data = await async_func(*args, **kwargs)
            # 发射成功信号
            result = AsyncResult(success=True, data=data)
            self._async_result_signal.emit((request_id, result))
        except Exception as e:
            # 发射失败信号
            result = AsyncResult(success=False, error=e)
            self._async_result_signal.emit((request_id, result))
    
    @Slot(object)
    def _handle_result(self, data):
        """处理结果（在主线程中）"""
        request_id, result = data
        callback = self._async_callbacks.get(request_id)
        if callback:
            callback(result)
        # 清理回调
        self._async_callbacks.pop(request_id, None)


class AsyncHelper(QObject):
    """
    独立的异步请求助手类
    
    用于不方便使用混入类的场景
    """
    result_signal = Signal(object)
    
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.callbacks = {}
        self.result_signal.connect(self._handle_result)
    
    def request(
        self,
        async_func: Callable,
        callback: Optional[Callable[[AsyncResult], None]] = None,
        *args,
        **kwargs
    ):
        """发起异步请求"""
        request_id = id(async_func) + id(args) + id(kwargs)
        self.callbacks[request_id] = callback
        
        asyncio.run_coroutine_threadsafe(
            self._execute(request_id, async_func, *args, **kwargs),
            self.loop
        )
    
    async def _execute(self, request_id: int, async_func: Callable, *args, **kwargs):
        """执行异步函数"""
        try:
            data = await async_func(*args, **kwargs)
            result = AsyncResult(success=True, data=data)
            self.result_signal.emit((request_id, result))
        except Exception as e:
            result = AsyncResult(success=False, error=e)
            self.result_signal.emit((request_id, result))
    
    @Slot(object)
    def _handle_result(self, data):
        """处理结果"""
        request_id, result = data
        callback = self.callbacks.get(request_id)
        if callback:
            callback(result)
        self.callbacks.pop(request_id, None)
