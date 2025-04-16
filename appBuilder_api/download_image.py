"""
    desc: |
      图片下载和内容理解模块
      主要功能：
      1. 从JSON中提取图片链接并下载
      2. 图片格式转换
      3. 图片内容理解
      4. 内容替换和保存
"""
import json
import requests
import os
import logging
import PIL
from PIL import Image
import sys
import re
from appBuilder_api import QianfanAppBuilderAPI

class ImageProcessor:
    """
    图片处理类"""
    def __init__(self, app_id, authorization, logger=None, 
                 image_links_path=['page_info', 'image_links'],
                 min_size_kb=30,
                 valid_response_key=None,
                 image_save_dir=None, retry_count=2, retry_delay=5):
        """
        初始化图片处理器
        :param app_id: 千帆API的app_id
        :param authorization: 千帆API的authorization
        :param logger: 外部传入的logger，如果为None则创建新的logger
        :param image_links_path: 图片链接在JSON中的路径，以列表形式表示，默认为['page_info', 'image_links']
        :param min_size_kb: 图片最小大小，单位为KB，默认为30
        :param valid_response_key: 模型返回结果中判断有效性的键名，如果为None则不进行有效性检查
        :param image_save_dir: 图片保存目录，如果为None则使用当前目录下的'images'文件夹
        """
        self.logger = logger or self._setup_logger()

        self.api_client = QianfanAppBuilderAPI(app_id, authorization, self.logger, retry_count, retry_delay)
        self.image_links_path = image_links_path
        self.min_size_bytes = min_size_kb * 1024
        self.valid_response_key = valid_response_key
        
        # 设置并创建图片保存目录
        self.image_save_dir = image_save_dir or os.path.join(os.getcwd(), 'images')
        os.makedirs(self.image_save_dir, exist_ok=True)
        self.logger.info("Images will be saved to: {}".format(self.image_save_dir))
        
        # 记录有效性检查配置
        if self.valid_response_key:
            self.logger.info("Validity check enabled with key: {}".format(self.valid_response_key))
        else:
            self.logger.info("Validity check disabled")

    def _setup_logger(self):
        """设置默认logger"""
        logger = logging.getLogger('ImageProcessor')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)  # 修改为DEBUG级别
        return logger

    def _get_image_format(self, image_path):
        """获取图片格式"""
        try:
            with Image.open(image_path) as img:
                self.logger.info("Image {} - Format: {}".format(image_path, img.format))
                return img.format
        except IOError:
            self.logger.error("Cannot open {}. It may not be a valid image file.".format(image_path))
            return None

    def _convert_to_jpg(self, source_file_path, target_file_path):
        """转换图片为JPG格式"""
        filename = os.path.basename(source_file_path)
        image_format = self._get_image_format(source_file_path)
        
        if not image_format:
            self.logger.error("Unable to determine the image format of {}".format(filename))
            return False, None

        if image_format in ['JPEG', 'JPG', 'PNG']:
            return True, source_file_path

        try:
            with Image.open(source_file_path) as img:
                target_path = os.path.join(target_file_path, "{}.jpg"\
                    .format(os.path.splitext(filename)[0]))
                rgb_im = img.convert('RGB')
                rgb_im.save(target_path, "JPEG")
                self.logger.info("Converted {} to JPG format.".format(source_file_path))
                os.remove(source_file_path)
                self.logger.info("Deleted original file {}.".format(source_file_path))
                return True, target_path
        except IOError:
            self.logger.error("Cannot convert {}. Unsupported image format or corrupted file."\
                .format(source_file_path))
            return False, None

    def _download_images(self, image_links, key):
        """下载图片并转换格式"""
        saved_files = {}
        for index, url in image_links.items():
            try:
                response = requests.get(url)
                response.raise_for_status()
                
                file_path = os.path.join(self.image_save_dir, "{}_{}.png".format(key, index))
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                    
                status, converted_path = self._convert_to_jpg(file_path, self.image_save_dir)
                if status:
                    saved_files[index] = os.path.abspath(converted_path)
                    self.logger.info("Image {} downloaded and saved as {}".format(index, converted_path))
            except requests.RequestException as e:
                self.logger.warning("Failed to download image {} from {}: {}".format(index, url, e))
        return saved_files

    def _call_image_understanding(self, image_path):
        """调用图片理解API"""
        try:
            with open(image_path, 'rb') as file:
                self.logger.info('Preparing to upload file...')
                conversation_id = self.api_client.create_conversation()
                file_id, _ = self.api_client.upload_file(file)

            if file_id and conversation_id:
                query = "按照要求理解图片内容并且进行输出"
                result = self.api_client.run_app_api(query, file_id)
                return result
        except Exception as e:
            self.logger.error("Error in image understanding: {}".format(str(e)))
            return None

    def process_content(self, json_dict, save_path=None):
        """
        处理JSON数据中的图片和内容
        :param json_dict: 输入的JSON数据
        :param save_path: 可选的保存路径
        :return: 处理后的内容
        """
        try:
            # 提取图片链接
            current_dict = json_dict
            for key in self.image_links_path[:-1]:
                current_dict = current_dict.get(key, {})
            image_links = current_dict.get(self.image_links_path[-1], {})
            
            if not image_links:
                self.logger.warning("No image links found in JSON data at path: {}".format(
                    ' -> '.join(self.image_links_path)))
                return None

            # 下载图片
            file_key = json_dict.get('key', 'default_key')
            saved_files = self._download_images(image_links, file_key)
            
            # 处理内容
            org_content = json_dict.get('page_info', {}).get('content_text', '')
            describe_string = '这是一张图片，通过markdown格式json语法代码块输出图片内容如下：'
            new_content = org_content

            # 处理每张图片
            for image_name, image_path in saved_files.items():
                if os.path.getsize(image_path) < self.min_size_bytes:
                    continue
                
                self.logger.info("Processing image: {}".format(image_path))
                result = self._call_image_understanding(image_path)
                if result and 'answer' in result:
                    answer = result['answer']
                    match = re.search(r'```json(.*?)```', answer, re.DOTALL)
                    if match:
                        try:
                            answer_dict = json.loads(match.group(1))
                            
                            # 有效性检查
                            should_process = True
                            if self.valid_response_key is not None:
                                # 检查键是否存在
                                if self.valid_response_key not in answer_dict:
                                    error_msg = "Specified validity key '{}' not found in API response".format(
                                        self.valid_response_key)
                                    self.logger.error(error_msg)
                                    raise KeyError(error_msg)
                                
                                # 获取有效性标志并规范化处理
                                valid_flag = answer_dict[self.valid_response_key]
                                self.logger.info("Found validity flag: {} = {}".format(
                                    self.valid_response_key, valid_flag))
                                
                                # 类型检查和值规范化
                                if isinstance(valid_flag, str):
                                    valid_flag = valid_flag.lower() in ['true', 'yes', '1', 't', 'y']
                                    self.logger.info("Converted string validity flag {}".format(valid_flag))
                                elif isinstance(valid_flag, bool):
                                    self.logger.info("Validity flag is already boolean: {}".format(valid_flag))
                                else:
                                    valid_flag = False
                                    self.logger.info("Invalid validity flag type, set to False")
                                
                                should_process = valid_flag
                            
                            if should_process:
                                # 使用正则表达式替换图片标记
                                pattern = r'\{\{' + re.escape(str(image_name)) + r'\}\}'
                                replacement = describe_string + answer
                                new_content = re.sub(pattern, replacement, new_content)
                                self.logger.info("Replaced image {} with content description".format(image_name))
                            else:
                                self.logger.info("Skipped image {} due to validity check".format(image_name))
                                
                        except json.JSONDecodeError:
                            self.logger.error("Failed to parse JSON from API response for image {}".format(image_name))
                        except KeyError as e:
                            self.logger.error(str(e))
                            raise
                    else:
                        self.logger.warning("No JSON content found in API response for image {}".format(image_name))
                else:
                    self.logger.warning("Invalid or empty API response for image {}".format(image_name))

            # 保存结果
            if save_path:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.logger.info("Content saved to {}".format(save_path))

            return new_content

        except Exception as e:
            self.logger.error("Error processing content: {}".format(str(e)))
            return None

class StrictImageProcessor(ImageProcessor):
    """
    严格格式图片处理器
    用于处理社交平台等严格字段存储的图片内容
    主要功能：
    1. 支持遍历黑名单key过滤
    2. 图片链接正则校验
    3. 优化字典遍历逻辑
    """
    def __init__(self, app_id, authorization, process_black_key=None, image_url_reg=None,
                 recursive_depth=5, min_size_kb=30, valid_response_key=None):
        """
        初始化
        :param app_id: 应用ID
        :param authorization: 授权信息
        :param process_black_key: 黑名单key列表
        :param image_url_reg: 图片URL正则表达式
        :param recursive_depth: 最大递归深度
        :param min_size_kb: 最小图片大小(KB)
        :param valid_response_key: API响应有效性检查键
        """
        super().__init__(app_id, authorization)
        self.process_black_key = process_black_key or []
        self.image_url_reg = re.compile(image_url_reg) if image_url_reg else None
        self.recursive_depth = recursive_depth
        self.min_size_bytes = min_size_kb * 1024
        self.valid_response_key = valid_response_key
        
        self.logger.info("跳过黑名单key: {}".format(', '.join(self.process_black_key)))
        if self.valid_response_key:
            self.logger.info("Validity check enabled with key: {}".format(self.valid_response_key))
        
        if self.image_url_reg:
            self.logger.info("使用正则表达式: {}".format(self.image_url_reg))

    def _validate_url(self, url):
        """
        验证URL是否符合规则
        :param url: URL字符串
        :return: bool
        """
        if not isinstance(url, str):
            self.logger.debug("URL不是字符串类型: {}".format(type(url)))
            return False
            
        if not url:
            self.logger.debug("URL为空")
            return False
            
        self.logger.debug("验证URL: {}".format(url))
        self.logger.debug("使用正则表达式: {}".format(self.image_url_reg))
        
        match = re.search(self.image_url_reg, url)
        if match:
            self.logger.debug("URL匹配成功: {}".format(match.group(0)))
            return True
        else:
            self.logger.debug("URL不匹配正则表达式")
            return False

    def _traverse_dict(self, data, depth=0, parent_key=''):
        """
        递归遍历字典
        :param data: 待遍历的数据
        :param depth: 当前递归深度
        :param parent_key: 父级key路径
        :return: list of tuples (key_path, value)
        """
        if depth > self.recursive_depth:
            self.logger.warning("达到最大递归深度{}".format(self.recursive_depth))
            return []

        results = []
        self.logger.debug("当前递归深度: {}, 父级路径: {}".format(depth, parent_key))
        self.logger.debug("当前数据类型: {}".format(type(data)))
        
        if isinstance(data, dict):
            self.logger.debug("字典keys: {}".format(list(data.keys())))
            for key, value in data.items():
                if key in self.process_black_key:
                    self.logger.info("跳过黑名单key: {}".format(key))
                    continue
                    
                current_path = "{}.{}".format(parent_key, key) if parent_key else key
                self.logger.debug("处理字典key: {}, 完整路径: {}".format(key, current_path))
                
                if isinstance(value, (dict, list)):
                    self.logger.debug("发现嵌套结构 {}, 类型: {}".format(current_path, type(value)))
                    results.extend(self._traverse_dict(value, depth + 1, current_path))
                elif isinstance(value, str):
                    self.logger.debug("发现字符串值: {} = {}...".format(current_path, value[:100]))
                    results.append((current_path, value))
                else:
                    self.logger.debug("跳过非字符串值: {}, 类型: {}".format(current_path, type(value)))
                    
        elif isinstance(data, list):
            self.logger.debug("列表长度: {}".format(len(data)))
            for i, item in enumerate(data):
                current_path = "{}[{}]".format(parent_key, i)
                self.logger.debug("处理列表项 {}, 完整路径: {}".format(i, current_path))
                
                if isinstance(item, (dict, list)):
                    self.logger.debug("发现嵌套结构 {}, 类型: {}".format(current_path, type(item)))
                    results.extend(self._traverse_dict(item, depth + 1, current_path))
                elif isinstance(item, str):
                    self.logger.debug("发现字符串值: {} = {}...".format(current_path, item[:100]))
                    results.append((current_path, item))
                else:
                    self.logger.debug("跳过非字符串值: {}, 类型: {}".format(current_path, type(item)))
        else:
            self.logger.debug("跳过非字典/列表数据: {}, 类型: {}".format(parent_key, type(data)))
                    
        self.logger.debug("当前层级({})找到的结果数: {}".format(depth, len(results)))
        return results

    def process_content(self, json_dict, save_path=None):
        """
        处理JSON数据中的图片和内容
        :param json_dict: 输入的JSON数据
        :param save_path: 可选的保存路径
        :return: 处理后的内容或None（处理失败）
        """
        try:
            # 遍历所有字段，获取URL和对应的路径
            all_fields = self._traverse_dict(json_dict)
            url_paths = {}  # 用于存储URL及其在字典中的路径
            
            # 提取合规的图片链接
            for path, value in all_fields:
                if self._validate_url(value):
                    self.logger.info("找到合规图片链接: {} = {}".format(path, value))
                    url_paths[value] = path
                
            if not url_paths:
                self.logger.warning("未找到合规的图片链接")
                return None
                
            # 处理每个URL
            for url, path in url_paths.items():
                try:
                    # 下载图片
                    response = requests.get(url)
                    response.raise_for_status()
                    temp_path = os.path.join(self.image_save_dir, "temp_{}.jpg".format(hash(url)))
                    
                    with open(temp_path, 'wb') as f:
                        f.write(response.content)
                    
                    # 检查文件大小
                    if os.path.getsize(temp_path) < self.min_size_bytes:
                        os.remove(temp_path)
                        continue
                    
                    # 处理图片
                    result = self._call_image_understanding(temp_path)
                    os.remove(temp_path)  # 处理完后删除临时文件
                    
                    if result and 'answer' in result:
                        answer = result['answer']
                        # 直接替换URL为图片描述
                        path_parts = path.split('.')
                        current_dict = json_dict
                        
                        # 遍历路径到倒数第二个元素
                        for part in path_parts[:-1]:
                            current_dict = current_dict.get(part, {})
                        
                        # 设置最后一个元素的值
                        last_part = path_parts[-1]
                        current_dict[last_part] = answer
                        self.logger.info("已替换URL的内容描述: {}".format(path))
                    else:
                        self.logger.warning("API响应无效或为空: {}".format(url))
                        
                except requests.RequestException as e:
                    self.logger.error("下载图片失败 {}: {}".format(url, str(e)))
                except Exception as e:
                    self.logger.error("处理图片失败 {}: {}".format(url, str(e)))
            
            # 保存结果
            if save_path:
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(json_dict, f, ensure_ascii=False, indent=2)
                self.logger.info("内容已保存到 {}".format(save_path))
            
            return json_dict
            
        except Exception as e:
            self.logger.error("处理内容时出错: {}".format(str(e)))
            return None

def main():
    """示例用法"""
    # 配置参数
    app_id = ""
    authorization = ""
    
    # 创建处理器实例 - 使用默认参数
    # processor = ImageProcessor(app_id, authorization)
    
    # 创建严格处理器实例
    processor = StrictImageProcessor(
        app_id=app_id,
        authorization=authorization,
        process_black_key=["detailImg_before_convert", "detailImg_before_bos"],  # 跳过这些key
        image_url_reg=r'https://antioneplatform\.bj\.bcebos\.com(/.*)?',  # 修改后的图片URL规则
        recursive_depth=5,  # 最大递归深度
        min_size_kb=30,  # 最小图片大小
        valid_response_key="is_valid"  # API响应有效性检查键
    )
    
    # 读取示例JSON文件
    file_path = "appBuilder_api/test.json"
    with open(file_path, 'r') as f:
        json_dict = json.load(f)
    
    # 处理内容并保存
    save_path = os.path.splitext(file_path)[0] + '_processed.txt'
    result = processor.process_content(json_dict['info']['input'], save_path)
    
    if result:
        print("处理成功完成")
    else:
        print("处理失败")

if __name__ == "__main__":
    main()