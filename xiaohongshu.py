import os
import json
import re
from typing import List, Tuple, Optional
from pathlib import Path
import datetime
import argparse
import sys
import httpx
from unsplash.api import Api as UnsplashApi
from unsplash.auth import Auth as UnsplashAuth
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def download_image(url: str, save_path: str) -> bool:
    """下载图片并保存到指定路径
    
    Args:
        url (str): 图片URL
        save_path (str): 保存路径
        
    Returns:
        bool: 是否成功下载并保存
    """
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        print(f"⚠️ 下载图片失败: {str(e)}")
        return False

class ContentOrganizer:
    def __init__(self):
        # 配置 OpenRouter API
        self.openrouter_api_key = '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'
        self.openrouter_app_name = 'xiaohongshu'
        self.openrouter_http_referer = 'https://github.com'
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # 配置API请求头
        self.headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "HTTP-Referer": self.openrouter_http_referer,
            "X-Title": self.openrouter_app_name,
            "Content-Type": "application/json"
        }
        
        # 选择要使用的模型
        self.AI_MODEL = "google/gemma-2-9b-it:free"
        
        # 测试API连接
        self.openrouter_available = self._test_api_connection()
        
        # 添加 Unsplash 配置
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        self.unsplash_client = None
        
        if self.unsplash_access_key:
            try:
                auth = UnsplashAuth(
                    client_id=self.unsplash_access_key,
                    client_secret=None,
                    redirect_uri=None
                )
                self.unsplash_client = UnsplashApi(auth)
                print("✅ Unsplash API 配置成功")
            except Exception as e:
                print(f"❌ Failed to initialize Unsplash client: {str(e)}")
    
    def _test_api_connection(self) -> bool:
        """测试OpenRouter API连接"""
        if not self.openrouter_api_key:
            print("⚠️ OpenRouter API key未设置")
            return False
        
        try:
            print("正在测试 OpenRouter API 连接...")
            response = requests.post(
                url=self.api_url,
                headers=self.headers,
                json={
                    "model": self.AI_MODEL,
                    "messages": [
                        {"role": "user", "content": "test"}
                    ]
                }
            )
            if response.status_code == 200:
                print("✅ OpenRouter API 连接测试成功")
                return True
            else:
                print(f"⚠️ OpenRouter API 连接测试失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️ OpenRouter API 连接测试失败: {str(e)}")
            return False

    def split_content(self, text: str, max_chars: int = 2000) -> List[str]:
        """按段落分割文本，保持上下文的连贯性"""
        if not text:
            return []

        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        last_paragraph = None
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_length = len(para)
            
            # 添加上一个chunk的最后一段作为上下文
            if not current_chunk and last_paragraph:
                current_chunk.append(f"上文概要：\n{last_paragraph}\n")
                current_length += len(last_paragraph) + 20
            
            # 处理超长段落
            if para_length > max_chars:
                if current_chunk:
                    last_paragraph = current_chunk[-1]
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                    if last_paragraph:
                        current_chunk.append(f"上文概要：\n{last_paragraph}\n")
                        current_length += len(last_paragraph) + 20
                
                # 按句子分割长段落
                sentences = re.split(r'([。！？])', para)
                current_sentence = []
                current_sentence_length = 0
                
                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    if i + 1 < len(sentences):
                        sentence += sentences[i + 1]
                    
                    if current_sentence_length + len(sentence) > max_chars and current_sentence:
                        chunks.append(''.join(current_sentence))
                        current_sentence = [sentence]
                        current_sentence_length = len(sentence)
                    else:
                        current_sentence.append(sentence)
                        current_sentence_length += len(sentence)
                
                if current_sentence:
                    chunks.append(''.join(current_sentence))
            else:
                if current_length + para_length > max_chars and current_chunk:
                    last_paragraph = current_chunk[-1]
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                    if last_paragraph:
                        current_chunk.append(f"上文概要：\n{last_paragraph}\n")
                        current_length += len(last_paragraph) + 20
                current_chunk.append(para)
                current_length += para_length
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks

    def organize_content(self, content: str) -> str:
        """使用AI整理内容"""
        if not self.openrouter_available:
            print("⚠️ OpenRouter API 未配置，将返回原始内容")
            return content

        # 构建系统提示词
        system_prompt = """你是一位著名的科普作家和博客作者，著作等身，屡获殊荣，尤其在内容创作领域有深厚的造诣。

                            请使用 4C 模型（建立联系 Connection、展示冲突 Conflict、强调改变 Change、即时收获 Catch) 为录的文字内容创建结构。

                            写作要求：
                            - 从用户的问题出发，引导读者理解核心概念及其背景
                            - 使用第二人称与读者对话，语气亲切平实
                            - 确保所有观点和内容基于用户提供的转录文本
                            - 如无具体实例，则不编造
                            - 涉及复杂逻辑时，使用直观类比
                            - 避免内容重复冗余
                            - 逻辑递进清晰，从问题开始，逐步深入

                            Markdown格式要求：
                            - 第一行为书名
                            - 第二行为章节名
                            - 大标题突出主题，吸引眼球，最好使用疑问句
                            - 小标题简洁有力，结构清晰，尽量使用单词或短语
                            - 直入主题，在第一部分清晰阐述问题和需求
                            - 正文使用自然段，避免使用列表形式
                            - 内容翔实，避免过度简略，特别注意保留原文中的数据和示例信息
                            - 如有来源URL，使用文内链接形式
                            - 保留原文中的Markdown格式图片链接
                            
                            文件描述
                            - 上传的文件格式为：第一行书名、第二行章节名、剩下为章节内容
                            """

        try:
            response = requests.post(
                url=self.api_url,
                headers=self.headers,
                json={
                    "model": self.AI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"请根据以下内容创作一篇结构清晰、易于理解的博客文章：\n\n{content}"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('choices'):
                    return result['choices'][0]['message']['content'].strip()
            return content
            
        except Exception as e:
            print(f"⚠️ 内容整理失败: {str(e)}")
            return content

    def _get_unsplash_images(self, query: str, count: int = 3) -> List[str]:
        """从Unsplash获取相关图片"""
        if not self.unsplash_client:
            print("⚠️ Unsplash客户端未初始化")
            return []
            
        try:
            # 将查询词翻译成英文以获得更好的结果
            if self.openrouter_available:
                try:
                    response = requests.post(
                        url=self.api_url,
                        headers=self.headers,
                        json={
                            "model": self.AI_MODEL,
                            "messages": [
                                {"role": "system", "content": "你是一个翻译助手。请将输入的中文关键词翻译成最相关的1-3个英文关键词，用逗号分隔。直接返回翻译结果，不要加任何解释。"},
                                {"role": "user", "content": query}
                            ],
                            "temperature": 0.3,
                            "max_tokens": 50
                        }
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('choices'):
                            query = result['choices'][0]['message']['content'].strip()
                except Exception as e:
                    print(f"⚠️ 翻译关键词失败: {str(e)}")
            
            # 使用httpx直接调用Unsplash API
            headers = {
                'Authorization': f'Client-ID {self.unsplash_access_key}'
            }
            
            all_photos = []
            for keyword in query.split(','):
                response = httpx.get(
                    'https://api.unsplash.com/search/photos',
                    params={
                        'query': keyword.strip(),
                        'per_page': count,
                        'orientation': 'portrait',
                        'content_filter': 'high'
                    },
                    headers=headers,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['results']:
                        photos = [photo['urls'].get('regular', photo['urls']['small']) 
                                for photo in data['results']]
                        all_photos.extend(photos)
            
            # 如果收集到的图片不够，用最后一个关键词继续搜索
            while len(all_photos) < count and query:
                response = httpx.get(
                    'https://api.unsplash.com/search/photos',
                    params={
                        'query': query.split(',')[-1].strip(),
                        'per_page': count - len(all_photos),
                        'orientation': 'portrait',
                        'content_filter': 'high',
                        'page': 2
                    },
                    headers=headers,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['results']:
                        photos = [photo['urls'].get('regular', photo['urls']['small']) 
                                for photo in data['results']]
                        all_photos.extend(photos)
                    else:
                        break
                else:
                    break
            
            return all_photos[:count]
            
        except Exception as e:
            print(f"⚠️ 获取图片失败: {str(e)}")
            return []

    def convert_to_xiaohongshu(self, content: str) -> Tuple[str, List[str], List[str], List[str]]:
        """将内容转换为小红书风格的笔记，并返回相关图片"""
        if not self.openrouter_available:
            print("⚠️ OpenRouter API 未配置，将返回原始内容")
            return content, [], [], []

        # 构建系统提示词
        system_prompt = """你是一位专业的小红书爆款文案写作大师，擅长将普通内容转换为刷屏级爆款笔记。
请将输入的内容转换为小红书风格的笔记，需要满足以下要求：

1. 标题创作（重要‼️）：
- 二极管标题法：
  * 追求快乐：产品/方法 + 只需N秒 + 逆天效果
  * 逃避痛苦：不采取行动 + 巨大损失 + 紧迫感
- 爆款关键词（必选1-2个）：
  * 高转化词：好用到哭、宝藏、神器、压箱底、隐藏干货、高级感
  * 情感词：绝绝子、破防了、治愈、万万没想到、爆款、永远可以相信
  * 身份词：小白必看、手残党必备、打工人、普通女生
  * 程度词：疯狂点赞、超有料、无敌、百分、良心推荐

2. 正文创作：
- 开篇设置（抓住痛点）：
  * 共情开场：描述读者痛点
  * 悬念引导：埋下解决方案的伏笔
  * 场景还原：具体描述场景
- 内容结构：
  * 每段开头用emoji引导
  * 重点内容加粗突出
  * 适当空行增加可读性
  * 步骤说明要清晰
- 结尾：
  * 结尾必须写明：以上信息来自于书名

3. 标签优化：
- 提取4类标签（除前三个标签外，每类1-2个）：
  * 前三个标签为：#阅读、#书名、#打卡
  * 核心关键词：主题相关
  * 关联关键词：长尾词
  * 高转化词：购买意向强
        
4. 文件描述
- 上传的文件格式为：第一行书名、第二行章节名、剩下为章节内容
"""

        try:
            response = requests.post(
                url=self.api_url,
                headers=self.headers,
                json={
                    "model": self.AI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"请将以下内容转换为爆款小红书笔记：\n\n{content}"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('choices'):
                    xiaohongshu_content = result['choices'][0]['message']['content'].strip()
                    
                    # 提取标题和标签
                    titles = []
                    content_lines = xiaohongshu_content.split('\n')
                    for line in content_lines:
                        line = line.strip()
                        if line and not line.startswith('#') and '：' not in line and '。' not in line:
                            titles = [line]
                            break
                    
                    tags = re.findall(r'#([^\s#]+)', xiaohongshu_content)
                    
                    # 获取相关图片
                    images = []
                    if self.unsplash_client:
                        search_terms = titles + tags[:2] if tags else titles
                        search_query = ' '.join(search_terms)
                        try:
                            images = self._get_unsplash_images(search_query, count=4)
                            if images:
                                print(f"✅ 成功获取{len(images)}张配图")
                            else:
                                print("⚠️ 未找到相关配图")
                        except Exception as e:
                            print(f"⚠️ 获取配图失败: {str(e)}")
                    
                    return xiaohongshu_content, titles, tags, images
                    
            return content, [], [], []
            
        except Exception as e:
            print(f"⚠️ 转换小红书笔记失败: {str(e)}")
            return content, [], [], []

    def process_markdown_file(self, input_file: str, output_dir: str = "output") -> None:
        """处理markdown文件，生成优化后的笔记
        
        Args:
            input_file (str): 输入的markdown文件路径
            output_dir (str): 输出目录路径（现在仅作为后备路径使用）
        """
        try:
            # 获取输入文件的目录作为输出目录
            input_path = Path(input_file)
            file_dir = input_path.parent
            
            # 读取markdown文件
            print(f"📝 正在读取Markdown文件: {input_file}")
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 生成时间戳
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 处理内容
            print("\n🔄 正在整理内容...")
            organized_content = self.organize_content(content)
            
            # 保存整理后的内容
            organized_file = os.path.join(file_dir, f"{timestamp}_organized.md")
            with open(organized_file, 'w', encoding='utf-8') as f:
                f.write(organized_content)
            print(f"✅ 整理后的内容已保存至: {organized_file}")
            
            # 生成小红书版本
            print("\n📱 正在生成小红书版本...")
            try:
                xiaohongshu_content, titles, tags, images = self.convert_to_xiaohongshu(organized_content)
                
                # 保存小红书版本
                xiaohongshu_file = os.path.join(file_dir, f"{timestamp}_xiaohongshu.md")
                
                # 下载并保存图片
                saved_images = []
                for i, image_url in enumerate(images, 1):
                    image_filename = f"图{i}.png"
                    image_path = os.path.join(file_dir, image_filename)
                    if download_image(image_url, image_path):
                        saved_images.append(image_filename)
                        print(f"✅ 已保存图片: {image_filename}")
                    else:
                        print(f"⚠️ 保存图片失败: {image_filename}")
                
                with open(xiaohongshu_file, "w", encoding="utf-8") as f:
                    # 写入标题
                    if titles:
                        f.write(f"# {titles[0]}\n\n")
                    
                    # 如果有图片，先写入第一张作为封面
                    if saved_images:
                        f.write(f"![封面图]({saved_images[0]})\n\n")
                    
                    # 写入正文内容的前半部分
                    content_parts = xiaohongshu_content.split('\n\n')
                    mid_point = len(content_parts) // 2
                    
                    # 写入前半部分
                    f.write('\n\n'.join(content_parts[:mid_point]))
                    f.write('\n\n')
                    
                    # 如果有第二张图片，插入到中间
                    if len(saved_images) > 1:
                        f.write(f"![配图]({saved_images[1]})\n\n")
                    
                    # 写入后半部分
                    f.write('\n\n'.join(content_parts[mid_point:]))
                    
                    # 如果有第三张图片，插入到末尾
                    if len(saved_images) > 2:
                        f.write(f"\n\n![配图]({saved_images[2]})")
                    
                    # 写入标签
                    if tags:
                        f.write("\n\n---\n")
                        f.write("\n".join([f"#{tag}" for tag in tags]))
                        
                print(f"✅ 小红书版本已保存至: {xiaohongshu_file}")
                
            except Exception as e:
                print(f"⚠️ 生成小红书版本失败: {str(e)}")
                
        except Exception as e:
            print(f"⚠️ 处理Markdown文件时出错: {str(e)}")
            raise

def main():
    parser = argparse.ArgumentParser(description='内容整理和小红书笔记生成器')
    parser.add_argument('input', help='输入源：Markdown文件路径')
    parser.add_argument('--output', '-o', default='output', help='输出目录路径')
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input):
        print(f"⚠️ 输入文件不存在: {args.input}")
        sys.exit(1)
    
    # 检查输入文件是否是markdown文件
    if not args.input.endswith('.md'):
        print("⚠️ 输入文件必须是Markdown文件(.md)")
        sys.exit(1)
    
    # 创建ContentOrganizer实例并处理文件
    organizer = ContentOrganizer()
    organizer.process_markdown_file(args.input, args.output)

if __name__ == "__main__":
    main()
