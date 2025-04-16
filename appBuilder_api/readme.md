# QianfanAppBuilder API 封装

一个百度千帆AppBuilder API Python封装库，专注于图片理解和内容处理。

[![Version](https://img.shields.io/badge/version-1.3-blue.svg)](#)

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

### 基础用法

```python
from appBuilder_api import QianfanAppBuilderAPI

# 初始化API客户端
api = QianfanAppBuilderAPI(
    app_id="your_app_id",
    authorization="your_auth_token"
)

# 创建会话
conversation_id = api.create_conversation()

# 上传图片
with open("image.jpg", "rb") as file:
    file_id, _ = api.upload_file(file)

# 进行图片分析
result = api.run_app_api("分析这张图片的内容", file_id)
```

### 图片处理示例

```python
from appBuilder_api import ImageProcessor

# 初始化图片处理器
processor = ImageProcessor(
    app_id="your_app_id",
    authorization="your_auth_token",
    min_size_kb=30,
    valid_response_key="useful"
)
```

### StrictImageProcessor

继承自ImageProcessor的增强图片处理类，专门用于处理具有严格字段存储格式的图片内容（如社交平台数据）。

#### 参数

除继承自ImageProcessor的基础参数外，还包括：

- **process_black_key** (*Optional[List[str]]*) – 需要跳过处理的字段黑名单列表
- **image_url_reg** (*Optional[str]*) – 图片URL的正则表达式匹配规则
- **recursive_depth** (*int*) – 递归遍历JSON的最大深度，默认5

#### 特性

- 支持字段黑名单过滤，可跳过指定字段的处理
- 支持图片URL正则校验，确保处理的URL符合规范
- 优化的字典遍历逻辑，支持深度递归遍历
- 自动处理嵌套的JSON结构

#### 使用示例

```python
from appBuilder_api import StrictImageProcessor

# 初始化严格处理器实例
processor = StrictImageProcessor(
    app_id="your_app_id",
    authorization="your_auth_token",
    process_black_key=["detailImg_before_convert", "detailImg_before_bos"],  # 跳过这些字段
    image_url_reg=r'https://example\.com(/.*)?',  # 图片URL规则
    recursive_depth=5,  # 最大递归深度
    min_size_kb=30,  # 最小图片大小
    valid_response_key="is_valid"  # API响应有效性检查键
)

# 处理JSON数据
with open("data.json", "r") as f:
    json_data = json.load(f)
    result = processor.process_content(json_data)
```

## API 参考

### QianfanAppBuilderAPI

千帆AppBuilder API的主要封装类。

#### 参数

- **app_id** (*str*) – 应用ID
- **authorization** (*str*) – 认证token
- **logger** (*Optional[logging.Logger]*) – 自定义日志记录器
- **retry_count** (*int*) – API调用重试次数，默认3次
- **retry_delay** (*int*) – 重试等待时间（秒），默认10秒

#### 方法

##### create_conversation()

创建新的会话。

返回：
- **conversation_id** (*Optional[str]*) – 会话ID，失败时返回None

##### upload_file(file)
上传文件到平台。

参数：
- **file** (*BinaryIO*) – 要上传的文件对象

返回：
- **Tuple[Optional[str], Optional[str]]** – (file_id, conversation_id)元组

##### run_app_api(query, file_id=None)
调用应用API进行图片分析。

参数：
- **query** (*str*) – 查询文本
- **file_id** (*Optional[str]*) – 文件ID

返回：
- **Optional[Dict[str, Any]]** – API响应结果

### ImageProcessor

图片处理和内容理解的封装类。

#### 参数

- **app_id** (*str*) – 应用ID
- **authorization** (*str*) – 认证token
- **logger** (*Optional[logging.Logger]*) – 自定义日志记录器
- **image_links_path** (*List[str]*) – 图片链接在JSON中的路径，默认['page_info', 'image_links']
- **min_size_kb** (*int*) – 图片最小大小（KB），默认30
- **valid_response_key** (*Optional[str]*) – 结果有效性判断键
- **image_save_dir** (*Optional[str]*) – 图片保存目录
- **retry_count** (*int*) – 重试次数，默认2次
- **retry_delay** (*int*) – 重试等待时间，默认5秒

#### 方法

##### process_content(json_dict, save_path=None)
处理JSON数据中的图片和内容。

参数：
- **json_dict** (*Dict[str, Any]*) – 输入的JSON数据
- **save_path** (*Optional[str]*) – 结果保存路径

返回：
- **Optional[str]** – 处理后的内容

## 异常处理

所有API调用都包含完整的异常处理机制：

- `RequestException`: 网络请求异常
- `HTTPError`: API响应异常
- `IOError`: 文件操作异常
- `JSONDecodeError`: JSON解析异常

## 日志系统

内置完整的日志系统，记录：

- API调用状态和耗时
- 文件操作记录
- 错误和异常信息
- 重试机制状态

## 开发要求

- Python 3.6+
- 支持类型注解
- 支持异步操作（部分API）
- 支持重试机制（推理模型建议设置`retry_count`参数）
- 暂不支持stream模式
