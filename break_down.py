import os
from datetime import datetime
import re
import argparse
import sys

def read_text_file(file_path):
    """读取文本文件内容"""
    print(f"正在读取文件 {file_path}...", end='', flush=True)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        print("\r✓ 文件读取成功")
        return content
    except Exception as e:
        print("\r✗ 文件读取失败：", str(e))
        sys.exit(1)

def save_markdown(content, output_dir, book_name, chapter_name):
    """保存markdown文件"""
    print(f"正在保存章节 {chapter_name}...", end='', flush=True)
    try:
        # 从章节名中提取章节号
        chapter_num = ""
        chapter_match = re.search(r'第([一二三四五六七八九十百千\d]+)[章回]', chapter_name)
        if chapter_match:
            # 如果是中文数字，转换为阿拉伯数字
            cn_num = chapter_match.group(1)
            if cn_num.isdigit():
                chapter_num = cn_num
            else:
                # 中文数字到阿拉伯数字的映射
                cn_to_num = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
                           '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'}
                if cn_num in cn_to_num:
                    chapter_num = cn_to_num[cn_num]
                else:
                    chapter_num = "0"  # 默认值
        else:
            # 尝试匹配其他格式（如 Chapter 1）
            other_match = re.search(r'Chapter\s*(\d+)', chapter_name, re.IGNORECASE)
            if other_match:
                chapter_num = other_match.group(1)
            else:
                chapter_num = "0"

        # 创建目录
        chapter_dir = os.path.join(output_dir, book_name, chapter_name)
        os.makedirs(chapter_dir, exist_ok=True)
        
        # 构建文件名：原文_第X章.md
        file_name = f"原文_第{chapter_num}章.md"
        output_path = os.path.join(chapter_dir, file_name)
        
        # 在内容开头添加书名
        full_content = f"# {book_name}\n\n{content}"
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(full_content)
        
        print("\r✓ 章节保存成功：", output_path)
        return output_path
    except Exception as e:
        print("\r✗ 保存失败：", str(e))
        return None

def extract_book_name(content):
    """从内容中提取书名"""
    # 分割内容为行
    lines = content.strip().split('\n')
    
    # 尝试不同的模式匹配书名
    book_name = "未知书名"
    for line in lines[:10]:  # 只在前10行中查找
        # 尝试匹配 "书名：xxx" 或 "书名:xxx" 格式
        if ':' in line or '：' in line:
            name_match = re.search(r'[书名标题][:：]\s*(.+)', line)
            if name_match:
                book_name = name_match.group(1).strip()
                break
        # 尝试匹配 "《xxx》" 格式
        book_match = re.search(r'《(.+?)》', line)
        if book_match:
            book_name = book_match.group(1).strip()
            break
        # 尝试匹配开头的 "# xxx" 格式
        if line.startswith('#'):
            book_name = line.lstrip('#').strip()
            break
    
    # 移除书名中可能存在的markdown标记
    book_name = re.sub(r'^[#\s]*', '', book_name)  # 移除开头的#号和空格
    book_name = re.sub(r'[:：].*$', '', book_name)  # 移除冒号及其后面的内容
    return book_name.strip()

def split_into_chapters(content):
    """将内容分割成章节
    Returns:
        list: 包含章节信息的字典列表
    """
    print("正在分析章节结构...", end='', flush=True)
    try:
        # 分割内容为行
        lines = content.strip().split('\n')
        
        # 提取书名
        book_name = extract_book_name(content)
        
        # 查找所有章节的起始位置
        chapters = []
        current_chapter = None
        current_content = []
        
        # 章节标题的正则模式
        chapter_patterns = [
            # 匹配带有标题的章节格式（支持多级#）
            r'^#{1,2}\s*第[一二三四五六七八九十百千\d]+章\s*[^#\n]*',
            # 匹配带有标题的回格式
            r'^#{1,2}\s*第[一二三四五六七八九十百千\d]+回\s*[^#\n]*',
            # 匹配英文章节格式
            r'^#{1,2}\s*Chapter\s*\d+[^#\n]*',
            # 匹配数字章节格式
            r'^#{1,2}\s*\d+\s*[章回][^#\n]*'
        ]
        
        for line in lines:
            line = line.strip()
            # 检查是否是章节标题
            is_chapter_title = False
            chapter_match = None
            
            for pattern in chapter_patterns:
                chapter_match = re.match(pattern, line, re.IGNORECASE)
                if chapter_match:
                    is_chapter_title = True
                    break
            
            if is_chapter_title:
                # 如果已有章节，保存它
                if current_chapter and current_content:
                    chapters.append({
                        'chapter_name': current_chapter,
                        'content': '\n'.join(current_content).strip()
                    })
                # 开始新章节，保留完整的章节标题（包括章节代号和名称）
                current_chapter = chapter_match.group(0).strip()
                # 移除开头的 # 号
                current_chapter = re.sub(r'^#+\s*', '', current_chapter)
                current_content = []
            elif current_chapter is not None:  # 如果已经找到第一个章节
                current_content.append(line)
            
        # 保存最后一个章节
        if current_chapter and current_content:
            chapters.append({
                'chapter_name': current_chapter,
                'content': '\n'.join(current_content).strip()
            })
        
        print(f"\r✓ 章节分析完成，共找到 {len(chapters)} 个章节")
        return book_name, chapters
    
    except Exception as e:
        print(f"\r✗ 章节分析失败：{str(e)}")
        return None, []

def break_down_text(input_file, output_dir):
    """将文本按章节拆分"""
    # 读取文件
    content = read_text_file(input_file)
    if not content:
        return None
    
    try:
        # 分析并拆分章节
        book_name, chapters = split_into_chapters(content)
        
        if chapters:
            print(f"\n✓ 识别到书名：{book_name}")
            print(f"✓ 识别到 {len(chapters)} 个章节")
            
            # 保存章节
            saved_files = []
            for chapter in chapters:
                chapter_name = chapter['chapter_name']
                chapter_content = chapter['content']
                if chapter_content:
                    output_path = save_markdown(chapter_content, output_dir, book_name, chapter_name)
                    if output_path:
                        saved_files.append(output_path)
            
            if saved_files:
                print("\n✓ 所有章节处理完成！")
                print(f"✓ 共处理 {len(saved_files)} 个章节")
                return saved_files
            
        print("\r✗ 处理失败，未能保存任何章节")
        return None
            
    except Exception as e:
        print(f"\r✗ 处理过程中发生错误：{str(e)}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='将文本文件按章节拆分为markdown文件')
    parser.add_argument('input_file', help='输入文件路径')
    parser.add_argument('--output', '-o', default='output', help='输出目录路径 (默认: output)')
    
    args = parser.parse_args()
    input_file = os.path.abspath(args.input_file)
    output_dir = os.path.abspath(args.output)
    
    print("\n=== 开始处理文件 ===\n")
    
    if os.path.exists(input_file):
        break_down_text(input_file, output_dir)
    else:
        print(f"✗ 错误：输入文件 {input_file} 不存在")
    
    print("\n=== 处理完成 ===\n")