# -*- coding: utf-8 -*-
"""
生成 OCR 对照实验的测试图 B / C（图 A 为既有 homework_test.png）。

- 图 B（hard-handwriting.png）：低对比度 + 整体轻微旋转 + 楷体模拟手写 + 逐字抖动/旋转，
  4 题填空答案，含潦草符号（如把 2+a 写得连笔、分数线歪斜）。
- 图 C（mixed-messy.png）：多题混排（题目与答案交错、行距不均），含一处涂改划线
  （先写错误答案再划掉、旁边补写正确答案）。

ground truth 见 ground_truth.json。
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

random.seed(42)

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "images")
os.makedirs(IMG_DIR, exist_ok=True)

FONTS = {
    "yahei": r"C:\Windows\Fonts\msyh.ttc",
    "kai": r"C:\Windows\Fonts\simkai.ttf",
    "fang": r"C:\Windows\Fonts\simfang.ttf",
}


def font(name, size):
    return ImageFont.truetype(FONTS[name], size)


def add_noise(img, strength=6):
    px = img.load()
    w, h = img.size
    for _ in range(w * h // 40):
        x, y = random.randrange(w), random.randrange(h)
        r, g, b = px[x, y]
        d = random.randint(-strength, strength)
        px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)))


def draw_jittered_text(base, xy, text, fnt, fill, max_rot=4.0, max_dy=3, spacing=0):
    """逐字抖动 + 轻微旋转，模拟手写不整齐"""
    x, y = xy
    for ch in text:
        ch_img = Image.new("RGBA", (fnt.size + 20, fnt.size + 30), (0, 0, 0, 0))
        d = ImageDraw.Draw(ch_img)
        d.text((10, 6), ch, font=fnt, fill=fill)
        ch_img = ch_img.rotate(random.uniform(-max_rot, max_rot), expand=True, resample=Image.BICUBIC)
        base.paste(ch_img, (int(x), int(y + random.uniform(-max_dy, max_dy))), ch_img)
        x += d.textlength(ch, font=fnt) + spacing


def gen_image_b():
    """低对比度 + 旋转 + 手写风格，4 题"""
    W, H = 900, 760
    img = Image.new("RGB", (W, H), (238, 236, 228))  # 泛黄纸
    ink = (105, 105, 110)  # 低对比度灰墨

    title_f = font("kai", 40)
    body_f = font("kai", 33)

    d = ImageDraw.Draw(img)
    d.text((60, 40), "周末作业（自测）", font=title_f, fill=ink)

    lines = [
        ("1. 已知 a=log3 2，则 log3 18 = ______（用 a 表示）", False),
        ("   答：2+a", True),
        ("2. 函数 f(x)=√3·sinx+cosx 的最大值为 ______", False),
        ("   答：2", True),
        ("3. 计算 ∫(0→1) x^2 dx = ______", False),
        ("   答：1/3", True),
        ("4. 若 x+y=5，xy=3，则 x^2+y^2 = ______", False),
        ("   答：19", True),
    ]
    y = 130
    for text, sloppy in lines:
        if sloppy:
            # 答案部分逐字抖动，模拟潦草
            draw_jittered_text(img, (70, y), text, body_f, ink, max_rot=6.0, max_dy=4)
        else:
            draw_jittered_text(img, (60, y), text, body_f, ink, max_rot=1.5, max_dy=1)
        y += 74

    img = img.rotate(2.2, expand=False, resample=Image.BICUBIC, fillcolor=(238, 236, 228))
    add_noise(img, 8)
    path = os.path.join(IMG_DIR, "B_hard_handwriting.png")
    img.save(path)
    return path


def gen_image_c():
    """多题混排 + 涂改划线"""
    W, H = 900, 700
    img = Image.new("RGB", (W, H), (252, 252, 250))
    ink = (30, 30, 30)
    q_f = font("yahei", 30)
    a_f = font("kai", 30)

    d = ImageDraw.Draw(img)
    d.text((50, 30), "课堂练习", font=font("yahei", 36), fill=ink)

    # 第 1 题：题目和学生答案写同一行区域，答案先写错再划掉改正
    d.text((50, 100), "1. 解方程 x^2-5x+6=0", font=q_f, fill=ink)
    d.text((70, 145), "解：x=2", font=a_f, fill=ink)
    # 涂改：在“x=2”上划两条斜线
    d.line([(75, 165), (170, 150)], fill=ink, width=3)
    d.line([(75, 152), (170, 168)], fill=ink, width=3)
    d.text((190, 142), "改为：x=2 或 x=3", font=a_f, fill=ink)

    # 第 2 题：题目下面紧跟答案，行距很窄
    d.text((50, 215), "2. 求 f(x)=x^3-3x 的极值点", font=q_f, fill=ink)
    d.text((70, 250), "x=1 和 x=-1", font=a_f, fill=ink)

    # 第 3 题：题目与下一题题目之间夹着答案（混排）
    d.text((50, 310), "3. 已知 tanα=2，求 (sinα+cosα)/(sinα-cosα)", font=q_f, fill=ink)
    d.text((70, 355), "原式=3", font=a_f, fill=ink)
    d.text((50, 420), "4. 计算 log2 8", font=q_f, fill=ink)
    d.text((70, 465), "log2 8=3", font=a_f, fill=ink)

    # 页面污渍
    d.ellipse([(700, 550), (760, 610)], outline=(210, 200, 180), width=8)
    add_noise(img, 4)
    path = os.path.join(IMG_DIR, "C_mixed_messy.png")
    img.save(path)
    return path


if __name__ == "__main__":
    b = gen_image_b()
    c = gen_image_c()
    print("saved:", b)
    print("saved:", c)
