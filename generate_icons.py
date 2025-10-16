import json
import os
import re
import subprocess

from pathlib import Path
from PIL import Image, ImageColor, ImageDraw, ImageFont

# LAYER_CONFIGS = {
#   16: {
#     'LABEL': True,
#     'LABEL_TEXT': (8, 10, 5, '#fff', '_fonts/3x5 MT Pixel.ttf')
#   },
#   # 32: {
#   #   'LABEL': True,
#   #   'LABEL_TEXT': (11, 5, 7, '#fff', 'segoeuib.ttf'),
#   #   'LOGO': (16, 21, 16)
#   # },
#   48: {
#     'LABEL': True,
#     'LABEL_TEXT': (16, 8, 8, '#fff', 'segoeuib.ttf'),
#     'LOGO': (24, 30, 22)
#   },
#   256: {
#     'LABEL': True,
#     'LABEL_TEXT': (87, 44, 42, '#fff', 'segoeuib.ttf'),
#     'LOGO': (128, 160, 120)
#   }
# }

LAYER_CONFIGS = {
  16: {
    'SHEET': False,
    'LOGO': (8, 8, 16),
  },
  48: {
    'LABEL_TEXT': (22, 31, 10, '#555', 'segoeuib.ttf'),
    'LOGO': (24, 24, 20),
    'LOWERCASE': True
  },
  256: {
    'LABEL_TEXT': (122, 172, 44, '#555', 'segoeuib.ttf'),
    'LOGO': (128, 128, 104),
    'LOWERCASE': True
  }
}

base_dir = Path.cwd()
layers_dir = base_dir / '_layers'
logos_dir = base_dir / '_logos'
png_output_dir = base_dir / 'png'
png_output_dir.mkdir(exist_ok = True)
ico_output_dir = base_dir / 'ico'
ico_output_dir.mkdir(exist_ok = True)

def main():
  generate_png()
  generate_ico()

def generate_png():
  with open(base_dir / 'types.json') as f:
    types_data = json.load(f)

  for item in types_data:
    for extension in item['extensions']:
      logo_name = item.get('logo') or extension
      tint_hex = item['tint']
      tint_logo = item.get('tintLogo', False)

      logo_path = logos_dir / f'{logo_name}.png'
      if not logo_path.exists():
        print(f'Logo not found: {logo_path}')
        continue

      logo_img = Image.open(logo_path).convert('RGBA')
      if tint_logo:
        logo_img = tint_image(logo_img, tint_hex)

      for size, layer_config in LAYER_CONFIGS.items():
        sheet_file = layers_dir / f'sheet_{size}px.png'
        if layer_config.get('SHEET') is False or not sheet_file.exists():
          combined = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        else:
          combined = Image.open(sheet_file).convert('RGBA')

        type_folder = png_output_dir / extension
        type_folder.mkdir(exist_ok = True)

        file_name = type_folder / f'{size}px.png'
        if os.path.exists(file_name):
          continue

        if 'LABEL' in layer_config:
          label_path = layers_dir / f'label_{size}px.png'
          if not label_path.exists():
            print(f'Label image not found: {label_path}, skipping')
            continue

          label_img = Image.open(label_path).convert('RGBA')
          label_img = tint_image(label_img.resize(combined.size, Image.Resampling.LANCZOS), tint_hex)
          label_layer = Image.new('RGBA', combined.size, (0, 0, 0, 0))
          label_layer.paste(label_img, (0, 0), label_img)
          combined = Image.alpha_composite(combined, label_layer)

        if 'LABEL_TEXT' in layer_config:
          text_x, baseline_y, text_font_size, text_color, text_font = layer_config['LABEL_TEXT']
          font = ImageFont.truetype(text_font, text_font_size)
          text = item.get('text') or (f'.{extension.lower()}' if layer_config.get('LOWERCASE') else extension.upper())

          text_bbox = font.getbbox(text)
          text_width = text_bbox[2] - text_bbox[0]
          text_height = text_bbox[3] - text_bbox[1]

          text_img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
          text_draw = ImageDraw.Draw(text_img)
          text_draw.text((-text_bbox[0], -text_bbox[1]), text, fill = ImageColor.getrgb(text_color), font = font)

          centered_text_x = text_x - text_img.width // 2
          text_layer = Image.new('RGBA', combined.size, (0, 0, 0, 0))
          text_layer.alpha_composite(text_img, (centered_text_x, baseline_y + text_bbox[1]))
          combined = Image.alpha_composite(combined, text_layer)

        if 'LOGO' in layer_config:
          centered_logo_x, centered_logo_y, logo_size = layer_config['LOGO']
          aspect_ratio = logo_img.width / logo_img.height

          width = int(logo_size * aspect_ratio)
          height = logo_size
          if width > combined.width:
            width = combined.width
            height = int(width / aspect_ratio)
          resized_logo = logo_img.resize((width, height), Image.Resampling.BILINEAR)

          layer = Image.new('RGBA', combined.size, (0, 0, 0, 0))
          logo_x = centered_logo_x - width // 2
          logo_y = centered_logo_y - height // 2
          layer.paste(resized_logo, (logo_x, logo_y), resized_logo)
          combined = Image.alpha_composite(combined, layer)

        combined.save(file_name)
      print(f'Saved {type_folder}.')

def generate_ico():
  for folder in os.listdir(png_output_dir):
    folder_path = os.path.join(png_output_dir, folder)
    if not os.path.isdir(folder_path):
      continue

    images = []
    for file in os.listdir(folder_path):
      match = re.match(r'(\d+)px\.png$', file)
      if match:
        size = int(match.group(1))
        images.append((size, os.path.join(folder_path, file)))

    if not images:
      continue

    images.sort(key=lambda x: x[0], reverse=True)
    image_files = [img[1] for img in images]
    output_file = os.path.join(ico_output_dir, folder + '.ico')

    subprocess.run(['magick', 'convert', *image_files, output_file])
    print(f'Saved {output_file}.')

def tint_image(img, tint_hex):
  if len(tint_hex) == 4:
    tint_hex = '#' + ''.join([c*2 for c in tint_hex[1:]])
  tint_rgb = tuple(int(tint_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
  r, g, b, a = img.split()
  r = r.point(lambda i: min(int(i * tint_rgb[0] / 255), 255))
  g = g.point(lambda i: min(int(i * tint_rgb[1] / 255), 255))
  b = b.point(lambda i: min(int(i * tint_rgb[2] / 255), 255))
  return Image.merge('RGBA', (r, g, b, a))

main()
