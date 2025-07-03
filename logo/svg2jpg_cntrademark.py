import os
import io
from PIL import Image, ImageOps
import cairosvg

# 配置参数
dir_path = os.path.dirname(os.path.abspath(__file__))
min_size = 300
max_size = 1500
dpi = 300
max_file_size = 2 * 1024 * 1024  # 2MB

for filename in os.listdir(dir_path):
    if filename.lower().endswith('v7.svg'):
        svg_path = os.path.join(dir_path, filename)
        jpg_name = os.path.splitext(filename)[0] + '.jpg'
        jpg_path = os.path.join(dir_path, jpg_name)

        # 先用cairosvg转为PNG（支持高DPI）
        png_bytes = cairosvg.svg2png(url=svg_path, dpi=dpi)
        img = Image.open(io.BytesIO(png_bytes))

        # 转为RGB灰度（黑白）
        img = ImageOps.grayscale(img).convert('RGB')

        # 调整尺寸到合规范围
        w, h = img.size
        scale = 1.0
        if w < min_size or h < min_size:
            scale = max(min_size / w, min_size / h)
        elif w > max_size or h > max_size:
            scale = min(max_size / w, max_size / h)
        if scale != 1.0:
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        # 保存为JPG，尝试不同质量以控制文件大小
        for quality in range(95, 10, -5):
            with io.BytesIO() as buf:
                img.save(buf, format='JPEG', quality=quality, dpi=(dpi, dpi))
                size = buf.tell()
                if size <= max_file_size:
                    with open(jpg_path, 'wb') as f:
                        f.write(buf.getvalue())
                    print(f'Saved {jpg_name} ({size // 1024}KB, quality={quality})')
                    break
        else:
            print(f'Warning: {jpg_name} 超过2MB，已用最低质量保存')
            img.save(jpg_path, format='JPEG', quality=10, dpi=(dpi, dpi))
