#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PWA 图标生成器
从 static/img/logo.png 生成所有尺寸的图标
"""

import os
from PIL import Image, ImageDraw, ImageFont

def create_icon(size, output_path):
    """创建指定尺寸的图标"""
    # 创建渐变背景
    img = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(img)
    
    # 渐变背景 (粉色到紫色)
    for y in range(size):
        # 从 #ec4899 到 #8b5cf6 的渐变
        r = int(236 + (139 - 236) * y / size)
        g = int(72 + (92 - 72) * y / size)
        b = int(153 + (246 - 153) * y / size)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    
    # 添加圆角
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size, size], radius=size//8, fill=255)
    
    # 应用圆角遮罩
    output = Image.new('RGBA', (size, size))
    output.paste(img, (0, 0))
    output.putalpha(mask)
    
    # 添加文字 "色"
    try:
        # 尝试使用系统中文字体
        font_size = int(size * 0.5)
        font_paths = [
            'C:\\Windows\\Fonts\\msyh.ttc',  # 微软雅黑
            'C:\\Windows\\Fonts\\simhei.ttf',  # 黑体
            '/System/Library/Fonts/PingFang.ttc',  # macOS
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # Linux
        ]
        
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        
        if font is None:
            font = ImageFont.load_default()
        
        # 绘制文字
        text = "色"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((size - text_width) // 2, (size - text_height) // 2 - int(size * 0.05))
        
        # 添加阴影效果
        shadow_offset = max(2, size // 100)
        draw.text((position[0] + shadow_offset, position[1] + shadow_offset), text, font=font, fill=(0, 0, 0, 100))
        draw.text(position, text, font=font, fill='white')
        
    except Exception as e:
        print(f"⚠️ 添加文字失败: {e}")
    
    # 保存图标
    output.save(output_path, 'PNG', optimize=True)
    print(f"✅ 生成图标: {output_path} ({size}x{size})")

def main():
    """主函数"""
    print("🎨 开始生成 PWA 图标...")
    
    # 创建目录
    icon_dir = 'static/icons'
    os.makedirs(icon_dir, exist_ok=True)
    
    # 需要生成的尺寸
    sizes = [72, 96, 128, 144, 152, 180, 192, 384, 512]
    
    # 生成所有尺寸的图标
    for size in sizes:
        output_path = os.path.join(icon_dir, f'icon-{size}x{size}.png')
        create_icon(size, output_path)
    
    # 生成 favicon.ico (16x16 和 32x32)
    print("\n🔖 生成 favicon...")
    favicon_sizes = [16, 32]
    favicon_images = []
    
    for size in favicon_sizes:
        img = Image.new('RGB', (size, size), color='white')
        draw = ImageDraw.Draw(img)
        
        # 简单的渐变
        for y in range(size):
            r = int(236 + (139 - 236) * y / size)
            g = int(72 + (92 - 72) * y / size)
            b = int(153 + (246 - 153) * y / size)
            draw.line([(0, y), (size, y)], fill=(r, g, b))
        
        favicon_images.append(img)
    
    # 保存 favicon.ico
    favicon_path = os.path.join(icon_dir, 'favicon.ico')
    favicon_images[0].save(favicon_path, format='ICO', sizes=[(16, 16), (32, 32)])
    print(f"✅ 生成 favicon: {favicon_path}")
    
    print("\n🎉 所有图标生成完成！")
    print(f"📁 图标位置: {icon_dir}")

if __name__ == '__main__':
    try:
        from PIL import Image, ImageDraw, ImageFont
        main()
    except ImportError:
        print("❌ 需要安装 Pillow 库")
        print("运行: pip install Pillow")

