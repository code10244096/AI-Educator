"""
清理空文件夹和命名不规范的文件夹
"""

import os
import shutil

BASE_DIR = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"

def main():
    print("=" * 60)
    print("清理空文件夹和重命名不规范文件夹")
    print("=" * 60)
    
    # 需要重命名的文件夹映射
    renames = {
        "新课标ⅰ": "新课标I卷",
        "新课标ⅱ": "新课标II卷",
        "新课标ⅲ": "新课标III卷",
        "全国卷Ⅲ": "全国卷III",
    }
    
    # 1. 先处理重命名
    print("\n步骤1: 重命名不规范文件夹")
    for old_name, new_name in renames.items():
        old_path = os.path.join(BASE_DIR, old_name)
        new_path = os.path.join(BASE_DIR, new_name)
        
        if os.path.exists(old_path):
            files = os.listdir(old_path)
            if files:
                # 如果目标文件夹已存在,合并文件
                if os.path.exists(new_path):
                    print(f"  合并: {old_name} -> {new_name} (目标已存在)")
                    for f in files:
                        src = os.path.join(old_path, f)
                        dst = os.path.join(new_path, f)
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                            print(f"    移动: {f}")
                        else:
                            print(f"    跳过: {f} (已存在)")
                    shutil.rmtree(old_path)
                    print(f"    删除空文件夹: {old_name}")
                else:
                    os.rename(old_path, new_path)
                    print(f"  重命名: {old_name} -> {new_name}")
            else:
                os.rmdir(old_path)
                print(f"  删除空文件夹: {old_name}")
        else:
            print(f"  跳过: {old_name} (不存在)")
    
    # 2. 清理空文件夹
    print("\n步骤2: 清理空文件夹")
    for folder in sorted(os.listdir(BASE_DIR)):
        folder_path = os.path.join(BASE_DIR, folder)
        if os.path.isdir(folder_path):
            files = os.listdir(folder_path)
            # 过滤掉非json文件
            json_files = [f for f in files if f.endswith('.json')]
            if not json_files:
                shutil.rmtree(folder_path)
                print(f"  删除空文件夹: {folder}")
            else:
                print(f"  保留: {folder} ({len(json_files)}个文件)")
    
    # 3. 列出最终结果
    print("\n" + "=" * 60)
    print("最终文件夹列表:")
    print("=" * 60)
    for folder in sorted(os.listdir(BASE_DIR)):
        folder_path = os.path.join(BASE_DIR, folder)
        if os.path.isdir(folder_path):
            files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
            print(f"  {folder}: {len(files)}个文件")

if __name__ == "__main__":
    main()
