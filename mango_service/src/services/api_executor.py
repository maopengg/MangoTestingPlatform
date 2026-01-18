import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from src.models import ApiTest, TestResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime


class ApiTestExecutor:
    """
    API测试执行器，负责执行API测试用例
    """
    
    @staticmethod
    async def execute_api_test(api_test: ApiTest) -> Dict[str, Any]:
        """
        执行单个API测试
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 解析请求头
            headers = {}
            if api_test.headers:
                try:
                    headers = json.loads(api_test.headers)
                except json.JSONDecodeError:
                    headers = {}
            
            # 解析请求体
            data = None
            if api_test.body:
                try:
                    data = json.loads(api_test.body)
                except json.JSONDecodeError:
                    data = api_test.body
            
            # 发起HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=api_test.method,
                    url=api_test.url,
                    headers=headers,
                    json=data if isinstance(data, dict) else None,
                    data=data if isinstance(data, str) else None
                ) as response:
                    response_text = await response.text()
                    response_json = {}
                    
                    # 尝试解析JSON响应
                    try:
                        response_json = await response.json()
                    except:
                        pass
                    
                    duration = int((asyncio.get_event_loop().time() - start_time) * 1000)  # 转换为毫秒
                    
                    # 返回测试结果
                    result = {
                        'status_code': response.status,
                        'response_text': response_text,
                        'response_json': response_json,
                        'duration': duration,
                        'success': response.status < 400,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    return result
        except Exception as e:
            duration = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return {
                'error': str(e),
                'duration': duration,
                'success': False,
                'timestamp': datetime.utcnow().isoformat()
            }

    @staticmethod
    async def execute_test_case(db_session: AsyncSession, api_test_id: int) -> Optional[TestResult]:
        """
        执行测试用例并保存结果
        """
        # 获取API测试定义
        api_test_result = await db_session.execute(
            select(ApiTest).where(ApiTest.id == api_test_id)
        )
        api_test = api_test_result.scalar_one_or_none()
        
        if not api_test:
            return None
        
        # 执行测试
        execution_result = await ApiTestExecutor.execute_api_test(api_test)
        
        # 创建测试结果记录
        test_result = TestResult(
            test_case_id=api_test_id,  # 在这种情况下，API测试ID作为测试用例ID
            status='PASSED' if execution_result.get('success', False) else 'FAILED',
            result_data=json.dumps(execution_result),
            duration=execution_result.get('duration', 0)
        )
        
        db_session.add(test_result)
        await db_session.commit()
        await db_session.refresh(test_result)
        
        return test_result
