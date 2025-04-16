# /Users/liluyu01/llm/黑产agent/批量微信公众号json处理/评估/d6de2002e38aba599e7d2400fd0914ff_image3.png
# https://antioneplatform.bj.bcebos.com/public_opinion_image/click/test/42ce2c2985b46132eaea7243575b2c99

import PIL 
from PIL import Image
import requests
import os

image_links = {'image3': 'https://antioneplatform.bj.bcebos.com/public_opinion_image/click/test/42ce2c2985b46132eaea7243575b2c99'}
image_dir = '/Users/liluyu01/llm/黑产agent/批量微信公众号json处理/评估/'
key = 'd6de2002e38aba599e7d2400fd0914ff'


for index, url in image_links.items():
    response = requests.get(url)
    response.raise_for_status()
    print("Downloading image from {}".format(url))
    
    file_path = os.path.join(image_dir, "{}_{}.png".format(key, index))
    print("Saving image to {}".format(file_path))
    with open(file_path, 'wb') as f:
        f.write(response.content)
        


#image_path="/Users/liluyu01/llm/黑产agent/批量微信公众号json处理/评估/d6de2002e38aba599e7d2400fd0914ff_image3.png"

with Image.open(file_path) as img:
    print("Image {} - Format: {}".format(file_path, img.format))
    print(img.size, img.format)
    image_format = img.format

if not file_path:
    print("Cannot open {}. It may not be a valid image file.".format(image_path))

filename = os.path.basename(file_path)
if image_format in ['JPEG', 'JPG', 'PNG']:
    print("Image format is valid.")
else:
    print("begin convert to JPG.")

    with Image.open(file_path) as img:
        target_path = os.path.join(image_dir, "{}.jpg"\
            .format(os.path.splitext(filename)[0]))
        print("Saving image to {}".format(target_path))
        rgb_im = img.convert('RGB')
        rgb_im.save(target_path, "JPEG")
        print("Converted {} to JPG format.".format(file_path))
        os.remove(file_path)
        print("Deleted original file {}.".format(file_path))
