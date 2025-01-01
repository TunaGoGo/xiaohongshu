import re
import jieba
from collections import Counter
import json
import sys
import os

def count_word_frequency(file_path):
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误：文件 '{file_path}' 不存在")
        sys.exit(1)
        
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用jieba进行中文分词
    words = jieba.cut(content)
    
    # 过滤掉标点符号和空白字符
    words = [word for word in words if re.match(r'[\u4e00-\u9fa5a-zA-Z0-9]+', word)]
    
    # 统计词频
    word_counts = Counter(words)
    
    # 按照频率降序排序
    sorted_word_counts = dict(sorted(word_counts.items(), key=lambda x: x[1], reverse=True))
    
    # 获取输入文件所在的目录
    output_dir = os.path.dirname(file_path)
    output_file = os.path.join(output_dir, 'word_frequency_result.json')
    
    # 将结果写入新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_word_counts, f, ensure_ascii=False, indent=4)
    
    print(f"词频统计已完成，结果已保存到: {output_file}")
    return sorted_word_counts

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("使用方法: python word_frequency.py <文件路径>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    # 处理Windows路径中的反斜杠
    file_path = file_path.replace('\\', '/')
    # 如果路径以 ./ 或 .\ 开头，去掉这个前缀
    if file_path.startswith('./') or file_path.startswith('.\\'):
        file_path = file_path[2:]
        
    result = count_word_frequency(file_path) 