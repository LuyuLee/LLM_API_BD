# 非多媒体情况下的图片处理方案

## 背景

- 之前的脚本处理的是多媒体情况下（图片和文字混合，如微信公众号)。但是在众人帮、小红书、微博等社交平台、网赚平台，图片有严格的字段存储，和之前格式不同。故需要新的处理方案
- 平台升级后图片处理不需要再进行convert转换或者resize了

## 方案

### 流程

- 通过入参找到待处理字典
- 遍历字典中每一个子key（递归直到类型为str)。遍历过程排除遍历黑名单key （新增逻辑)
- 确认图片链接是否合规（opt：image_url_reg)  （新增逻辑)
- 合规图片下载，检查图片大小是否超过min_size_kb （有变动，不再需要转变图片类型)
- 调用图片处理模块，返回图片描述
- 图片描述合规判定（opt：valid_response_key)
- 图片描述替换原本内容

### 入参设定

- app_id
- authorization
- logger
- image_links_path
- min_size_kb
- image_save_dir
- retry_count
- retry_delay
- process_black_key : 遍历黑名单key list 在里面的key不进行处理直接跳过
- image_url_reg:一个正则表达式，如果符合则表名是合规链接，否则跳过。默认None，None表示没有要求全部符合全部处理

### 类定义
```python
class StrictImageProcessor(ImageProcessor):
    """
    严格格式图片处理器（继承自ImageProcessor）
    新增功能：
    1. 支持遍历黑名单key过滤
    2. 图片链接正则校验
    3. 优化字典遍历逻辑
    """
    def __init__(self, process_black_key=None, image_url_reg=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process_black_key = process_black_key or []
        self.image_url_reg = re.compile(image_url_reg) if image_url_reg else None
```

### 参数说明表
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|-----|
| process_black_key | list | [] | 需要跳过的字典key列表 |
| image_url_reg | str | None | 图片链接必须匹配的正则表达式 |
| recursive_depth | int | 5 | 最大递归遍历深度防护 |

### 新增方法说明
```python
def _traverse_dict(self, data, depth=0):
    """
    递归遍历字典（带防护机制）
    返回所有末级字符串字段的路径
    """
    if depth > self.recursive_depth:
        self.logger.warning(f"达到最大递归深度{self.recursive_depth}")
        return []
```

### 新增逻辑详细说明

#### 遍历字典中每一个子key（递归直到类型为str)。遍历过程排除遍历黑名单key

- 遍历子key，对于每一个子key检查是否在process_black_key这个list中，如果在则跳过不处理。
- 如果遍历发现子key的类型是dict，则重复遍历；如果是str，则进入后续缓解；如果是其他类型，则不处理

#### 确认图片链接是否合规 

- 依赖参数 image_url_reg。默认为空，如果为空则说明不进行合规检测，直接进行下一步
- 对于待检测的图片链接，用image_url_reg检测是否匹配，不匹配则跳过。匹配则进行下一步
