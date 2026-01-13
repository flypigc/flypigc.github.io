import os
import re
import random
from pathlib import Path

def load_urls_dict(urls_file_path):
    """从字典文件加载URL列表，增强文件处理能力[1](@ref)"""
    urls = []
    try:
        with open(urls_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                url = line.strip()
                # 跳过空行、注释行和无效URL
                if not url or url.startswith('#'):
                    continue
                # 基础URL验证
                if re.match(r'^https?://', url):
                    urls.append(url)
                else:
                    print(f"警告: 第{line_num}行URL格式可能无效: {url}")
        
        print(f"成功加载 {len(urls)} 个有效URL地址")
        return urls
    except FileNotFoundError:
        print(f"错误: 字典文件 {urls_file_path} 未找到")
        return []
    except Exception as e:
        print(f"加载字典文件时出错: {e}")
        return []

def has_cover_attribute(content):
    """增强检查内容是否已包含cover属性[6](@ref)"""
    # 改进的正则模式，匹配更灵活的cover属性格式
    cover_patterns = [
        r'^cover:\s*.+',  # 标准格式
        r'^cover\s*:\s*.+',  # 允许空格
        r'^cover-image:\s*.+',  # 兼容cover-image
    ]
    
    lines = content.split('\n')
    in_front_matter = False
    front_matter_end = False
    
    for line in lines:
        line = line.strip()
        if line == '---':
            if in_front_matter:
                front_matter_end = True
                break
            else:
                in_front_matter = True
                continue
        
        if in_front_matter and not front_matter_end:
            for pattern in cover_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    return True
    
    return False

def add_cover_attribute(content, cover_url):
    """改进的cover属性添加逻辑，支持更多front matter格式[6](@ref)"""
    lines = content.split('\n')
    new_lines = []
    front_matter_count = 0
    cover_added = False
    has_front_matter = False
    
    # 检测是否已有front matter
    for i, line in enumerate(lines):
        if line.strip() == '---':
            front_matter_count += 1
            if front_matter_count == 2:
                has_front_matter = True
                break
    
    front_matter_count = 0
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # 检测front matter边界
        if line_stripped == '---':
            front_matter_count += 1
            new_lines.append(line)
            
            # 在第二个---之前添加cover属性
            if front_matter_count == 2 and not cover_added and has_front_matter:
                # 查找插入位置（在最后一个属性和---之间）
                insert_pos = len(new_lines) - 1
                while insert_pos > 0 and new_lines[insert_pos-1].strip() == '':
                    insert_pos -= 1
                
                # 确保前面有空行（如果不是第一个属性）
                if (insert_pos > 1 and 
                    new_lines[insert_pos-1].strip() != '' and 
                    not new_lines[insert_pos-1].startswith('---')):
                    new_lines.insert(insert_pos, '')
                    insert_pos += 1
                
                new_lines.insert(insert_pos, f'cover: {cover_url}')
                cover_added = True
            continue
        
        # 如果没有front matter，在开头创建
        if front_matter_count == 0 and not cover_added and not has_front_matter:
            new_lines.extend(['---', f'cover: {cover_url}', '---', ''])
            cover_added = True
            front_matter_count = 2  # 标记为已处理front matter
        
        new_lines.append(line)
    
    # 如果遍历完都没有添加cover（特殊情况处理）
    if not cover_added:
        if has_front_matter:
            # 有front matter但没找到插入位置，在开头添加
            new_content = f"---\ncover: {cover_url}\n" + '\n'.join(new_lines[1:])
            return new_content
        else:
            # 没有front matter，创建完整的
            new_content = f"---\ncover: {cover_url}\n---\n\n" + '\n'.join(new_lines)
            return new_content
    
    return '\n'.join(new_lines)

def validate_md_file(file_path):
    """验证MD文件是否有效"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return True, content
    except UnicodeDecodeError:
        try:
            # 尝试其他编码
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
            return True, content
        except:
            return False, None
    except Exception:
        return False, None

def backup_file(file_path):
    """创建文件备份"""
    backup_path = f"{file_path}.bak"
    try:
        with open(file_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        return True
    except Exception:
        return False

def process_md_files(directory_path, urls_dict_file):
    """改进的批量处理MD文件函数[6](@ref)"""
    # 加载URL字典
    urls = load_urls_dict(urls_dict_file)
    if not urls:
        default_url = "https://cdn.nlark.com/yuque/0/2026/jpeg/62156892/1768309323937-bff34426-7f34-495e-88b5-2ce52b52ea37.jpeg"
        urls = [default_url]
        print("使用默认URL进行后续处理")
    
    # 使用Path对象处理路径
    directory = Path(directory_path)
    if not directory.exists():
        print(f"错误: 目录 {directory_path} 不存在")
        return
    
    # 统计信息
    stats = {
        'processed': 0,
        'added_cover': 0,
        'skipped': 0,
        'errors': 0,
        'backup_failed': 0
    }
    
    # 支持多种MD文件扩展名
    md_extensions = {'.md', '.markdown'}
    
    # 遍历目录中的所有MD文件[1](@ref)
    for md_file in directory.rglob('*'):
        if md_file.suffix.lower() in md_extensions:
            stats['processed'] += 1
            relative_path = md_file.relative_to(directory)
            
            try:
                # 验证文件
                is_valid, content = validate_md_file(md_file)
                if not is_valid:
                    print(f"跳过 {relative_path}: 文件编码不支持")
                    stats['skipped'] += 1
                    continue
                
                # 检查是否已存在cover属性
                if has_cover_attribute(content):
                    print(f"跳过 {relative_path}: 已存在cover属性")
                    stats['skipped'] += 1
                    continue
                
                # 创建备份
                if not backup_file(md_file):
                    print(f"警告: 无法创建备份 {relative_path}")
                    stats['backup_failed'] += 1
                    # 继续处理，但不建议跳过
                
                # 随机选择URL
                cover_url = random.choice(urls)
                
                # 添加cover属性
                new_content = add_cover_attribute(content, cover_url)
                
                # 写回文件
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"处理成功 {relative_path}: 添加封面")
                stats['added_cover'] += 1
                
            except Exception as e:
                print(f"处理文件 {relative_path} 时出错: {e}")
                stats['errors'] += 1
    
    # 输出处理结果摘要
    print(f"\n=== 处理完成 ===")
    print(f"扫描目录: {directory_path}")
    print(f"处理文件总数: {stats['processed']}")
    print(f"成功添加封面: {stats['added_cover']}")
    print(f"跳过已有封面: {stats['skipped']}")
    print(f"处理错误: {stats['errors']}")
    if stats['backup_failed'] > 0:
        print(f"备份失败: {stats['backup_failed']} (建议检查文件权限)")

def main():
    """改进的主函数，支持命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='为MD文件批量添加随机封面URL')
    parser.add_argument('--dir', default='.', help='MD文件目录路径 (默认: 当前目录)')
    parser.add_argument('--urls', default='urlspic.txt', help='URL字典文件路径 (默认: urlspic.txt)')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份文件')
    
    args = parser.parse_args()
    
    # 验证目录是否存在
    if not os.path.exists(args.dir):
        print(f"错误: 目录 {args.dir} 不存在")
        return
    
    if not os.path.isdir(args.dir):
        print(f"错误: {args.dir} 不是一个有效的目录")
        return
    
    # 执行处理
    process_md_files(args.dir, args.urls)

if __name__ == "__main__":
    main()