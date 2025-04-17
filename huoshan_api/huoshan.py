import base64
import os
import logging
from volcenginesdkarkruntime import Ark

class ArkAPIClient:
    def __init__(self, api_key: str, model_id: str, logger: logging.Logger):
        self.client = Ark(api_key=api_key)
        self.model_id = model_id
        self.logger = logger
        self.logger.info("Initialized ArkAPIClient with model ID: %s", model_id)

    def encode_image(self, image_path: str) -> str:
        """将指定路径图片转为Base64编码"""
        try:
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                self.logger.info("Encoded image %s to base64", image_path)
                return encoded_image
        except Exception as e:
            self.logger.error("Failed to encode image %s: %s", image_path, e)
            raise

    def create_chat_completion(self, text: str, image_path: str):
        """创建一个对话请求，使用文本和图片"""
        self.logger.info("Creating chat completion for text: '%s' and image: '%s'", text, image_path)
        try:
            base64_image = self.encode_image(image_path)
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": text},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                        ],
                    }
                ],
            )
            self.logger.info("Received response from model")
            return response
        except Exception as e:
            self.logger.error("Error creating chat completion: %s", e)
            return None

def main():
    # 配置日志记录
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]  # 确保日志输出到终端（标准输出）
    )
    logger = logging.getLogger(__name__)

    # Initialize the Ark API client
    api_key = "2fd212a1-1865-485a-a261-b9013c551f8f"
    model_id = "doubao-1-5-vision-pro-32k-250115"
    client = ArkAPIClient(api_key=api_key, model_id=model_id, logger=logger)

    # Define the query text and image path
    query_text = "图片里讲了什么?"
    image_path = "358d0f232cd2af6372372caae9a78892_image3+.png"

    # Call the API and print the result
    response = client.create_chat_completion(query_text, image_path)
    if response:
        logger.info("Response: %s", response.choices[0])

if __name__ == "__main__":
    main()

# 写Readme.md