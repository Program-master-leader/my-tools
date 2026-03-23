#!/usr/bin/env python3
"""PDF合并工具 - 支持拖拽多文件、Word自动转PDF、交互式排序"""

import os
import sys
import re
import tempfile
import shutil


def parse_drag_input(raw):
    """解析Windows拖拽多文件输入
    Windows拖多个文件时格式为: path1"path2"path3 或 "path1""path2"
    路径之间可能有引号也可能没有，需要按盘符分割
    """
    raw = raw.strip()
    # 先统一去掉所有引号，再按 Windows 盘符（如 C:\ D:\）重新分割
    raw_clean = raw.replace('"', '')
    # 按盘符边界分割，保留盘符
    parts = re.split(r'(?=[A-Za-z]:\\)', raw_clean)
    paths = [p.strip() for p in parts if p.strip()]
    return paths


def convert_word_to_pdf(word_path, output_dir):
    """将Word文档转换为PDF，返回PDF路径"""
    try:
        from docx2pdf import convert
    except ImportError:
        print("  缺少依赖，正在提示安装: pip install docx2pdf")
        sys.exit(1)

    basename = os.path.splitext(os.path.basename(word_path))[0]
    pdf_path = os.path.join(output_dir, basename + ".pdf")
    print(f"  转换中: {os.path.basename(word_path)} -> {basename}.pdf")
    convert(word_path, pdf_path)
    return pdf_path


def collect_files(temp_dir):
    print("=" * 50)
    print("       PDF 合并工具")
    print("=" * 50)
    print("\n将所有文件一次性拖入终端窗口，然后按回车")
    print("支持 PDF 和 Word (.docx/.doc) 文件\n")

    raw = input("拖入文件: ")
    paths = parse_drag_input(raw)

    files = []
    for path in paths:
        path = path.strip('"').strip("'")
        if not os.path.isfile(path):
            print(f"  ✗ 文件不存在: {path}")
            continue

        ext = os.path.splitext(path)[1].lower()

        if ext == ".pdf":
            files.append(os.path.abspath(path))
            print(f"  ✓ {os.path.basename(path)}")

        elif ext in (".docx", ".doc"):
            pdf_path = convert_word_to_pdf(path, temp_dir)
            files.append(pdf_path)
            print(f"  ✓ 转换完成")

        else:
            print(f"  ✗ 不支持的格式: {os.path.basename(path)}")

    return files


def list_files(files):
    print("\n当前文件顺序：")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {os.path.basename(f)}")
    print()


def reorder_files(files):
    while True:
        list_files(files)
        print("操作: [m] 移动  [d] 删除  [a] 添加  [q] 确认合并")
        action = input("请选择: ").strip().lower()

        if action == "q":
            break

        elif action == "m":
            try:
                src = int(input("  将第几个文件移动？")) - 1
                dst = int(input("  移动到第几位？")) - 1
                if 0 <= src < len(files) and 0 <= dst < len(files):
                    files.insert(dst, files.pop(src))
                else:
                    print("  序号超出范围")
            except ValueError:
                print("  请输入有效数字")

        elif action == "d":
            try:
                idx = int(input("  删除第几个文件？")) - 1
                if 0 <= idx < len(files):
                    print(f"  已删除: {os.path.basename(files.pop(idx))}")
                else:
                    print("  序号超出范围")
            except ValueError:
                print("  请输入有效数字")

        elif action == "a":
            raw = input("  拖入或输入文件路径: ")
            paths = parse_drag_input(raw)
            for path in paths:
                path = path.strip('"').strip("'")
                ext = os.path.splitext(path)[1].lower()
                if not os.path.isfile(path):
                    print(f"  ✗ 文件不存在: {path}")
                elif ext == ".pdf":
                    files.append(os.path.abspath(path))
                    print(f"  ✓ 已添加: {os.path.basename(path)}")
                elif ext in (".docx", ".doc"):
                    pdf_path = convert_word_to_pdf(path, temp_dir)
                    files.append(pdf_path)
                    print(f"  ✓ 转换并添加完成")
                else:
                    print(f"  ✗ 不支持的格式: {os.path.basename(path)}")

    return files


def merge_pdfs(files, output_path):
    from pypdf import PdfWriter
    writer = PdfWriter()
    print("\n正在合并：")
    for path in files:
        print(f"  + {os.path.basename(path)}")
        writer.append(path)
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"\n✓ 合并完成 -> {output_path}")


def main():
    temp_dir = tempfile.mkdtemp()
    try:
        files = collect_files(temp_dir)

        if not files:
            print("\n没有有效文件，退出")
            input("按回车关闭...")
            sys.exit(0)

        files = reorder_files(files)

        if not files:
            print("文件列表为空，退出")
            input("按回车关闭...")
            sys.exit(0)

        output = input("输出文件名（默认 output.pdf）: ").strip()
        if not output:
            output = "output.pdf"
        if not output.lower().endswith(".pdf"):
            output += ".pdf"

        merge_pdfs(files, output)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    input("\n按回车关闭...")


if __name__ == "__main__":
    main()
