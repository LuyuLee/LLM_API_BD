# 方舟 SDK 使用指南

这是一个用于与方舟 SDK 交互的 Python 脚本示例，主要用于图片编码和对话请求创建。

## 功能特点

- 图片编码为 Base64
- 调用方舟 SDK 进行对话请求
- 日志记录输出到终端
- 完善的异常处理

## 环境要求

- Python 3.x
- 依赖库: `base64`, `logging`, `volcenginesdkarkruntime`（方舟SDK）

## 脚本说明

### ArkAPIClient

主要类，封装了与方舟 SDK 的所有交互。

#### 初始化参数

- `api_key`: API 密钥
- `model_id`: 模型 ID
- `logger`: （可选）日志记录器

```python
client = ArkAPIClient(api_key="your_api_key", model_id="your_model_id")
# 上传本地图片，需要将指定路径的图片转为 Base64 编码
encode_image(image_path: str) -> str
参数: image_path (str) - 图片文件路径
返回: Base64 编码字符串

# 创建一个对话请求，使用文本和图片
create_chat_completion(text: str, image_path: str)
参数:
text: 查询文本query
image_path: 图片文件路径
返回: 对话请求的响应结果

# 日志记录
使用 Python 标准库 logging 进行日志记录
默认输出到终端，包含操作时间、日志级别、消息内容
错误处理
该实现包含完善的错误处理机制：
    所有关键操作都有 try-catch 保护
    详细的日志记录，包含：操作时间戳｜错误详情｜使用示例

### ArkAPIClient 使用示例
import logging

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# 初始化参数
api_key = "your_api_key"
model_id = "your_model_id"
image_path = "path_to_your_image.png"
query_text = "图片里讲了什么?"

# 创建 API 客户端实例
client = ArkAPIClient(api_key=api_key, model_id=model_id)

try:
    # 调用 API
    response = client.create_chat_completion(query_text, image_path)
    
    if response:
        logging.info("Response: %s", response.choices[0])
        
except Exception as e:
    logging.error("Error: %s", str(e))

#### 注意事项
1. 确保提供正确的 API 密钥和模型 ID: https://www.volcengine.com/docs/82379/1330310(查询地址)
2. 图片文件路径需正确且可访问，支持的图片格式包括: jpg, jpeg, png，详情可查：https://www.volcengine.com/docs/82379/1362931#5f46bf24
3. 所有操作都有详细的日志记录