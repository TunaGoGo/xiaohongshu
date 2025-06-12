from PIL import Image, ImageDraw
import os

def create_grid_background(width=1080, height=1440, cell_size=20, line_color=(230, 230, 230)):
    # 创建一个白色背景的图片
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # 绘制垂直线
    for x in range(0, width + 1, cell_size):
        draw.line([(x, 0), (x, height)], fill=line_color, width=1)
    
    # 绘制水平线
    for y in range(0, height + 1, cell_size):
        draw.line([(0, y), (width, y)], fill=line_color, width=1)
    
    # 确保输出目录存在
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 保存图片
    output_path = os.path.join(output_dir, 'grid_background.png')
    image.save(output_path, 'PNG')
    print(f"网格背景图片已保存到: {output_path}")
    return output_path

if __name__ == '__main__':
    # 创建1080x1440像素的网格背景图片
    create_grid_background() 