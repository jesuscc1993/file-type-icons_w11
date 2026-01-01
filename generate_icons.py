import json
import os
import re
import subprocess

from pathlib import Path
from PIL import Image, ImageColor, ImageDraw, ImageFont

LAYER_CONFIGS = {
  16: {
    'SHEET': False,
    'LOGO': (8, 8, 16),
  },
  48: {
    'LABEL_TEXT': (24, 32, 10, '#555', 'segoeuib.ttf'),
    'LOGO': (24, 24, 20)
  },
  256: {
    'LABEL_TEXT': (128, 175, 44, '#555', 'segoeuib.ttf'),
    'LOGO': (128, 128, 104)
  }
}

OVERWRITE = {
  'LABEL': False,
  'LABEL_TEXT': False,
  'LOGO': False
}

base_dir = Path.cwd()
layers_dir = base_dir / '_layers/v1'
logos_dir = base_dir / '_logos'

png_dir = base_dir / 'png'
ico_dir = base_dir / 'ico'
png_dir.mkdir(exist_ok = True)
ico_dir.mkdir(exist_ok = True)

textless_png_dir = png_dir / '_textless'
textless_ico_dir = ico_dir / '_textless'
textless_png_dir.mkdir(exist_ok = True)
textless_ico_dir.mkdir(exist_ok = True)

def main():
  generate_png()
  generate_ico(png_dir, ico_dir)
  generate_ico(textless_png_dir, textless_ico_dir)
  input(f'Finished generating icons.')

def generate_png():
  with open(base_dir / 'types.json') as f:
    types_data = json.load(f)

  for item in types_data:
    for extension in item['extensions']:
      logo_name = item.get('logo') or extension
      tint_hex = item.get('tint')
      tint_logo = item.get('tintLogo', False)

      if not any(OVERWRITE.values()):
        pending_files = False
        for size in LAYER_CONFIGS.keys():
          file_name = png_dir / extension / f'{size}px.png'
          if not file_name.exists():
            pending_files = True
            break
        if not pending_files:
          print(f'Skipping "{extension}" extension as all PNG files already exist.')
          continue

      logo_path = logos_dir / f'{logo_name}.png'
      if not logo_path.exists():
        print(f'Logo not found: {logo_path}')
        continue

      logo_img = Image.open(logo_path).convert('RGBA')
      if tint_logo:
        logo_img = tint_image(logo_img, tint_hex)

      for size, layer_config in LAYER_CONFIGS.items():
        type_folder = png_dir / extension
        type_folder.mkdir(exist_ok = True)

        file_name = type_folder / f'{size}px.png'
        file_exists = os.path.exists(file_name)
        if file_exists:
          if not any(OVERWRITE.values()):
            continue
          combined = Image.open(file_name).convert('RGBA')
        else:
          sheet_file = layers_dir / f'sheet_{size}px.png'
          if layer_config.get('SHEET') is False or not sheet_file.exists():
            combined = Image.new('RGBA', (size, size), (0, 0, 0, 0))
          else:
            combined = Image.open(sheet_file).convert('RGBA')

        if 'LOGO' in layer_config and (not file_exists or OVERWRITE['LOGO']):
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

        # textless_folder = textless_png_dir / logo_name
        # textless_folder.mkdir(exist_ok = True)
        # textless_file_name = textless_folder / f'{size}px.png'
        # textless_file_exists = os.path.exists(textless_file_name)
        # if not textless_file_exists:
        #   textless_img = combined.copy()
        #   combined_alpha = combined.split()[3]
        #   textless_img.putalpha(combined_alpha)
        #   textless_img.save(textless_file_name)

        if 'LABEL' in layer_config and (not file_exists or OVERWRITE['LABEL']):
          label_path = layers_dir / f'label_{size}px.png'
          if not label_path.exists():
            print(f'Label image not found: {label_path}, skipping')
            continue

          label_img = Image.open(label_path).convert('RGBA')
          label_img = tint_image(label_img.resize(combined.size, Image.Resampling.LANCZOS), tint_hex)
          label_layer = Image.new('RGBA', combined.size, (0, 0, 0, 0))
          label_layer.paste(label_img, (0, 0), label_img)
          combined = Image.alpha_composite(combined, label_layer)

        if 'LABEL_TEXT' in layer_config and (not file_exists or OVERWRITE['LABEL_TEXT']):
          text_x, baseline_y, text_font_size, text_color, text_font = layer_config['LABEL_TEXT']
          font = ImageFont.truetype(text_font, text_font_size)
          text = item.get('text') or (f'.{extension.lower()}' if layer_config.get('LOWERCASE') else extension.upper())

          text_bbox = font.getbbox(text)
          text_width = text_bbox[2] - text_bbox[0]
          text_height = text_bbox[3] - text_bbox[1]

          text_img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
          text_draw = ImageDraw.Draw(text_img)
          if file_exists and OVERWRITE['LABEL_TEXT']:
            text_draw.rectangle([0, 0, text_width, text_height], fill = (255, 255, 255, 255))
          text_draw.text((-text_bbox[0], -text_bbox[1]), text, fill = ImageColor.getrgb(text_color), font = font)

          centered_text_x = text_x - text_img.width // 2
          text_layer = Image.new('RGBA', combined.size, (0, 0, 0, 0))
          text_layer.alpha_composite(text_img, (centered_text_x, baseline_y + text_bbox[1]))
          combined = Image.alpha_composite(combined, text_layer)

        combined.save(file_name)

      print(f'Processed {type_folder}.')

def generate_ico(src_dir, dest_dir):
  for folder in os.listdir(src_dir):
    folder_path = os.path.join(src_dir, folder)
    if not os.path.isdir(folder_path):
      continue

    images = []
    output_file = os.path.join(dest_dir, folder + '.ico')
    output_exists = os.path.exists(output_file)
    output_mtime = os.path.getmtime(output_file) if output_exists else 0

    for file in os.listdir(folder_path):
      match = re.match(r'(\d+)px\.png$', file)
      if match:
        file_path = os.path.join(folder_path, file)
        if not output_exists or os.path.getmtime(file_path) > output_mtime:
          images.append((int(match.group(1)), file_path))

    if not images:
      print(f'Skipping "{folder}" as PNG are unchanged.')
      continue

    images.sort(key=lambda x: x[0], reverse=True)
    image_files = [img[1] for img in images]

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
