"""
    last_update: 2025-03-26
"""

import requests
import json
import time
import os
import logging
from typing import Optional, Tuple, Dict, Any

class QianfanAppBuilderAPI(object):
    """千帆AppBuilder API的封装类，用于图片理解相关操作"""
    
    def __init__(self, app_id, authorization, logger=None, retry_count=3, retry_delay=10):
        """
        初始化千帆AppBuilder API客户端
        
        Args:
            app_id: 应用ID
            authorization: 认证token
            logger: 外部传入的logger对象，如果为None则使用默认配置
            retry_count: 重试次数，默认3次
            retry_delay: 重试等待时间（秒），默认10秒
        """
        self.app_id = app_id
        self.authorization = authorization
        self.conversation_id = None  # 当前会话ID
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        # 定义需要重试的错误码组
        self.retry_status_codes = [500, 424]
        
        # 使用传入的logger或创建新的logger
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            if not self.logger.handlers:  # 只有在没有handler时才添加
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '[%(asctime)s] - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
    
    def _make_request(self, method, url, headers, data=None, files=None):
        """
        发送HTTP请求，包含重试逻辑
        
        Args:
            method: HTTP方法
            url: 请求URL
            headers: 请求头
            data: 请求数据
            files: 文件数据
            
        Returns:
            Response对象，失败返回None
        """
        current_retry = 0
        
        while True:
            try:
                start_time = time.time()
                response = requests.request(method, url, headers=headers, data=data, files=files)
                elapsed_time = time.time() - start_time
                
                if response.status_code in self.retry_status_codes and current_retry < self.retry_count:
                    current_retry += 1
                    self.log("API call failed with status code: {}. Retrying ({}/{}) after {} seconds...".format(
                        response.status_code, current_retry, self.retry_count, self.retry_delay), level='warning')
                    time.sleep(self.retry_delay)
                    continue
                
                if response.status_code != 200:
                    self.log("API call failed with status code: {}. Elapsed time: {:.2f} seconds".format(
                        response.status_code, elapsed_time), level='error')
                else:
                    self.log("API call successful. Elapsed time: {:.2f} seconds".format(elapsed_time))
                
                return response
                
            except Exception as e:
                if current_retry < self.retry_count:
                    current_retry += 1
                    self.log("API call failed with error: {}. Retrying ({}/{}) after {} seconds...".format(
                        str(e), current_retry, self.retry_count, self.retry_delay), level='warning')
                    time.sleep(self.retry_delay)
                else:
                    self.log("API call failed after {} retries: {}".format(self.retry_count, str(e)), level='error')
                    return None
    
    def log(self, message, level='info'):
        """
        输出日志信息
        
        Args:
            message: 日志消息
            level: 日志级别，默认info
        """
        if level == 'error':
            self.logger.error(message)
        elif level == 'warning':
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def create_conversation(self):
        """
        创建新的会话，获取conversation_id
        
        Returns:
            str: 成功返回conversation_id，失败返回None
        """
        try:
            url = "https://qianfan.baidubce.com/v2/app/conversation"
            headers = {
                "X-Appbuilder-Authorization": self.authorization,
                'Content-Type': 'application/json'
            }
            payload = json.dumps({
                "app_id": self.app_id
            })
            
            response = self._make_request("POST", url, headers=headers, data=payload)
            if response and response.status_code == 200:
                self.conversation_id = response.json().get("conversation_id")
                self.log("Created new conversation with ID: {}".format(self.conversation_id))
                return self.conversation_id
            else:
                return None
            
        except Exception as e:
            self.log("Error creating conversation: {}".format(str(e)), level='error')
            return None

    def upload_file(self, file):
        """
        上传文件到平台
        注意：！！！ 如果有类中self.conversation_id不为None，
        则会使用类中self.conversation_id，否则会赋值一个新值。 
        这就说明类中的self.conversation_id优先级高于外部传入的conversation_id
        如果需要使用新的conversation_id，则需要先调用create_conversation()
        
        Args:
            file: 打开的文件对象
            
        Returns:
            Tuple[str, str]: (file_id, conversation_id)，失败返回(None, None)
        """
        try:
            start_time = time.time()
            self.log('Starting file upload...')
            
            url = "https://qianfan.baidubce.com/v2/app/conversation/file/upload"
            headers = {
                'X-Appbuilder-Authorization': self.authorization
            }
            
            if self.conversation_id:
                payload = {
                    'app_id': self.app_id,
                    'conversation_id': self.conversation_id
                }
            else:
                payload = {
                    'app_id': self.app_id
                }
                
            files = [
                ('file', (file.name.split('/')[-1], file, 'image/png'))
            ]
            
            response = self._make_request("POST", url, headers=headers, data=payload, files=files)
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            if response and response.status_code == 200:
                result = response.json()
                if result.get('conversation_id'):
                    self.conversation_id = result.get('conversation_id')
                    self.log('Got new conversation ID from upload: {}'.format(self.conversation_id))
                
                self.log('File upload completed in {:.2f} seconds'.format(elapsed_time))
                return result.get('id'), result.get('conversation_id')
            else:
                return None, None
            
        except Exception as e:
            self.log("Error uploading file: {}".format(str(e)), level='error')
            return None, None

    def run_app_api(self, query, file_id=None):
        """
        调用应用API进行图片分析
        
        Args:
            query: 查询文本
            file_id: 文件ID，可选
            
        Returns:
            Dict: API响应结果，失败返回None
        """
        try:
            if not self.conversation_id:
                if not self.create_conversation():
                    return None
            
            start_time = time.time()
            self.log('Starting API call...')
            
            url = "https://qianfan.baidubce.com/v2/app/conversation/runs"
            headers = {
                'Content-Type': 'application/json',
                'X-Appbuilder-Authorization': self.authorization
            }
            
            payload_dict = {
                "app_id": self.app_id,
                "query": query,
                "stream": False,
                "conversation_id": self.conversation_id
            }
            
            if file_id:
                payload_dict["file_ids"] = [file_id]
                
            payload = json.dumps(payload_dict)
            
            response = self._make_request("POST", url, headers=headers, data=payload)
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            if response and response.status_code == 200:
                self.log('API call completed in {:.2f} seconds'.format(elapsed_time))
                return response.json()
            else:
                return None
                
        except Exception as e:
            self.log("Error in API call: {}".format(str(e)), level='error')
            return None

    def get_status(self):
        """
        获取当前实例的状态信息，用于调试
        
        Returns:
            Dict: 包含当前实例所有重要参数的字典
        """
        status = {
            "app_id": self.app_id,
            "authorization": "***{}".format(self.authorization[-8:]),  # 只显示末尾几位
            "conversation_id": self.conversation_id
        }
        self.log("Current status: {}".format(json.dumps(status, indent=2)))
        return status


def main():
    """示例用法"""
    # 配置日志（这里仅作为示例，实际使用时可以使用外部的日志配置）
    logger = logging.getLogger("qianfan_example")
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(asctime)s] - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # 配置参数
    #app_id = "92189580-c467-4d66-9dc0-2fa9c94e3dc4"
    app_id = "e49c8a76-deb6-4e1e-834f-7ff4b5c0d465"
    app_id = "f1758d00-62f6-466c-9e10-b19c91e4b254"
    authorization = ""
    #file_path = '/Users/liluyu01/llm/wx/image/358d0f232cd2af6372372caae9a78892_image3+.png'
    file_path = ''
    file_id = None

    try:
        # 创建API实例，传入已配置的logger
        api = QianfanAppBuilderAPI(app_id, authorization, logger=logger)
        
        # 输出初始状态
        api.get_status()
        
        # 创建新会话
        api.create_conversation()
        api.get_status()
        
        # 上传文件
        with open(file_path, 'rb') as file:
            file_id, conv_id = api.upload_file(file)
            if not file_id:
                raise Exception("File upload failed")
        
        # 示例查询
        query = """
        按要求识别网站的截图中的内容并且按照要求判定后输出
        """
        
        # 运行API调用
        result = api.run_app_api(query, file_id)
        if result:
            api.log("API Response: {}".format(json.dumps(result, indent=2, ensure_ascii=False)))
        
    except Exception as e:
        logger.error("Error in main: {}".format(str(e)))

if __name__ == '__main__':
    main()