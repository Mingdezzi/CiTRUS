# 파일 경로: tabs/easel/services/image_service.py (Debug Prints Added)

from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont
import math
import traceback # For detailed error printing
# --- import 경로 수정 ---
from ..models.layer import Layer, ImageLayer, TextLayer, ShapeLayer, SAVE_IMG_MAX_SIZE, DISPLAY_IMG_MAX_SIZE
from .font_service import FontService
# --- 수정 끝 ---

try:
    from rembg import remove
    REMBG_AVAILABLE = True
    print("DEBUG: rembg library imported successfully.") # Debug print
except ImportError:
    REMBG_AVAILABLE = False
    print("DEBUG: rembg library not found.") # Debug print


class ImageService:
    """최종 이미지 생성, 저장 및 배경 제거 등 이미지 관련 서비스를 제공"""

    @staticmethod
    def save_canvas_as_image(settings, layers, canvas_objects):
        # canvas_objects 에는 로고 정보가 없음, settings 에서 logo_info 확인
        if not any(l.is_visible.get() for l in layers) and 'logo_info' not in settings:
            messagebox.showwarning("알림", "캔버스에 저장할 항목이 없습니다.")
            return "저장할 항목 없음."

        save_w = settings['output_width']
        save_h = settings['output_height']
        bg_color_hex = settings['background_color']

        try:
            bg_color = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        except:
            bg_color = (255, 255, 255, 255)

        final_image = Image.new("RGBA", (save_w, save_h), bg_color)

        # 렌더링 순서: 레이어 (아래 -> 위) -> 로고 (최상위)
        visible_layers = [l for l in layers if l.is_visible.get()] # is_visible 체크 유지

        # 1. 레이어 렌더링
        for layer in visible_layers: # 리스트 순서대로 (아래부터)
            obj_info = canvas_objects.get(layer.path)
            if not obj_info: continue

            center_x, center_y = obj_info['rel_x'] * save_w, obj_info['rel_y'] * save_h
            layer_img = ImageService._render_layer_to_pil(layer, save_w, save_h, settings)

            if layer_img:
                w, h = layer_img.size
                paste_pos = (int(center_x - w / 2), int(center_y - h / 2))
                # Paste 대신 alpha_composite 사용 (투명도 처리 개선)
                temp_layer_image = Image.new("RGBA", final_image.size, (0, 0, 0, 0))
                temp_layer_image.paste(layer_img, paste_pos, layer_img) # 마스크로 layer_img 사용
                final_image = Image.alpha_composite(final_image, temp_layer_image)

        # 2. 로고 렌더링 (레이어 위에)
        logo_info = settings.get('logo_info')
        if logo_info and 'pil_img_original' in logo_info:
            try:
                logo_pil_original = logo_info['pil_img_original']
                logo_scale = settings['logo_size']

                logo_target_h = save_h * (settings['logo_zone_height'] / 1500.0) * (logo_scale / 100.0)
                if logo_pil_original.height > 0:
                    logo_ratio = logo_target_h / logo_pil_original.height
                    logo_final_w, logo_final_h = int(logo_pil_original.width * logo_ratio), int(logo_target_h)

                    if logo_final_w > 0 and logo_final_h > 0:
                        logo_to_paste = logo_pil_original.resize((logo_final_w, logo_final_h), Image.Resampling.LANCZOS)
                        logo_center_x, logo_center_y = logo_info['rel_x'] * save_w, logo_info['rel_y'] * save_h
                        logo_paste_pos = (int(logo_center_x - logo_final_w / 2), int(logo_center_y - logo_final_h / 2))

                        temp_logo_image = Image.new("RGBA", final_image.size, (0, 0, 0, 0))
                        temp_logo_image.paste(logo_to_paste, logo_paste_pos, logo_to_paste) # 마스크로 logo_to_paste 사용
                        final_image = Image.alpha_composite(final_image, temp_logo_image)

            except Exception as e:
                print(f"로고 렌더링 중 오류 발생: {e}")

        # 파일 저장
        output_format = settings['output_format']
        fname = (settings['style_code'] or "thumbnail") + ('.png' if output_format == "PNG" else ".jpg")
        save_path = filedialog.asksaveasfilename(
            initialdir=settings['save_directory'],
            initialfile=fname,
            defaultextension=fname.split('.')[-1]
        )
        if not save_path:
            return "저장 취소."
        try:
            if output_format == "JPG":
                final_image.convert("RGB").save(save_path, "JPEG", quality=95)
            else:
                final_image.save(save_path, "PNG")
            messagebox.showinfo("성공", f"이미지를 저장했습니다.\n{save_path}")
            return "저장 완료!"
        except Exception as e:
            messagebox.showerror("저장 오류", f"파일 저장 중 오류 발생:\n{e}")
            return "저장 실패."

    # [ ★★★★★ 여기가 수정된 함수입니다 ★★★★★ ]
    @staticmethod
    def _render_layer_to_pil(layer: Layer, canvas_w, canvas_h, settings) -> Image.Image | None:
        scale = layer.scale_var.get()

        if isinstance(layer, TextLayer):
            font_size = int(scale)
            # [ ★★★★★ 수정: 'if' 문을 다음 줄로 분리 ★★★★★ ]
            if font_size < 1: 
                return None
                
            try: 
                font = ImageFont.truetype(FontService.get_font_path(layer.font_family), font_size)
            except IOError: 
                print(f"Warning: Font '{layer.font_family}' not found.")
                font = ImageFont.truetype(FontService.get_font_path('malgun.ttf'), font_size)
                
            bbox = font.getbbox(layer.text)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if text_w <= 0 or text_h <= 0: 
                return None
                
            txt_img = Image.new('RGBA', (text_w, text_h), (0, 0, 0, 0))
            d = ImageDraw.Draw(txt_img)
            d.text((-bbox[0], -bbox[1]), layer.text, font=font, fill=layer.color)
            
            return txt_img.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC) if layer.angle != 0 else txt_img

        elif isinstance(layer, ShapeLayer):
            shape_size = scale
            # [ ★★★★★ 수정: 'if' 문을 다음 줄로 분리 ★★★★★ ]
            if shape_size < 1: 
                return None
                
            if layer.shape_type != '자유곡선':
                points = layer._get_shape_points((0, 0), shape_size)
                if not points: 
                    return None
                if layer.angle != 0: 
                    points = ImageService._rotate_points(points, (0, 0), -layer.angle)
                    
                xs, ys = zip(*[(points[i], points[i+1]) for i in range(0, len(points), 2)]) # 수정: zip 사용
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                width, height = int(max_x - min_x) + 1, int(max_y - min_y) + 1
                if width <=0 or height <=0: 
                    return None
                    
                shape_img = Image.new('RGBA', (width, height), (0,0,0,0))
                shape_draw = ImageDraw.Draw(shape_img)
                shifted_points = [(x - min_x, y - min_y) for x, y in zip(xs, ys)]
                shape_draw.polygon(shifted_points, fill=layer.color)
                return shape_img
            else: # 자유곡선
                if not layer.pil_image: 
                    return None
                img = layer.pil_image
                scale_factor = scale / 100.0
                final_w, final_h = int(img.width * scale_factor), int(img.height * scale_factor)
                if final_w < 1 or final_h < 1: 
                    return None
                    
                img_to_paste = img.resize((final_w, final_h), Image.Resampling.LANCZOS)
                return img_to_paste.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC) if layer.angle != 0 else img_to_paste

        elif isinstance(layer, ImageLayer):
            try:
                if not hasattr(layer, 'pil_img_save') or layer.pil_img_save is None:
                    layer.pil_img_save = layer.pil_img_original.copy(); layer.pil_img_save.thumbnail(SAVE_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
                    print(f"Warning: Regenerated pil_img_save for {layer.path}")
                pil_to_process = layer.pil_img_save.crop(layer.crop_box) if layer.crop_box else layer.pil_img_save
            except Exception as e: 
                print(f"Error accessing/cropping pil_img_save for {layer.path}: {e}")
                return None
                
            scale_factor = scale / 100.0
            logo_zone_h = canvas_h * (settings['logo_zone_height'] / 1500.0)
            target_h = (canvas_h - logo_zone_h) * scale_factor
            
            # [ ★★★★★ MODIFIED: 내용물 크기 기준으로 비율 계산 ★★★★★ ]
            content_w, content_h = layer.get_content_dimensions()
            if content_h > 0:
                # content_h 기준으로 target_h 비율(ratio) 계산
                ratio = target_h / content_h
                # pil_to_process(전체 이미지)의 너비/높이에 ratio 적용하여 최종 크기 계산
                # (주의: content_w가 아닌 pil_to_process.width 사용)
                final_w, final_h = int(pil_to_process.width * ratio), int(pil_to_process.height * ratio)
                
                if final_w > 0 and final_h > 0:
                    try:
                        img_to_paste = pil_to_process.resize((final_w, final_h), Image.Resampling.LANCZOS)
                        if layer.angle != 0: 
                            img_to_paste = img_to_paste.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)
                        return img_to_paste
                    except Exception as e: 
                        print(f"Error resizing/rotating image {layer.path}: {e}")
                        return None
                else: 
                    print(f"Warning: Calculated final size is invalid for {layer.path}: {final_w}x{final_h}")
                    return None
            else: 
                print(f"Warning: Image content height is zero for {layer.path}.")
                return None
        return None

    # [ ★★★★★ 여기가 수정된 함수입니다 (Debug Prints Added) ★★★★★ ]
    @staticmethod
    def remove_background(layer: ImageLayer) -> bool:
        print(f"\n--- DEBUG: remove_background START for {layer.path} ---") # Debug print
        if not REMBG_AVAILABLE:
            print("DEBUG: rembg library is not available.") # Debug print
            messagebox.showerror("오류", "rembg 라이브러리를 사용할 수 없습니다.")
            return False
        if not isinstance(layer, ImageLayer):
            print(f"DEBUG: Layer is not ImageLayer (type: {type(layer)})") # Debug print
            messagebox.showerror("오류", "이미지 레이어가 아닙니다.")
            return False

        try:
            # [ ★★★★★ 수정 1: pil_img_save (저장용 이미지) 기반으로 배경 제거 ★★★★★ ]
            if not hasattr(layer, 'pil_img_save') or layer.pil_img_save is None:
                 print(f"DEBUG: pil_img_save not found for layer {layer.path}") # Debug print
                 messagebox.showerror("오류", f"이미지 레이어 '{layer.path}'의 처리용 이미지 데이터를 찾을 수 없습니다.")
                 print(f"--- DEBUG: remove_background END for {layer.path} (Failed: No pil_img_save) ---") # Debug print
                 return False

            print(f"DEBUG: Input image (pil_img_save) size: {layer.pil_img_save.size}, mode: {layer.pil_img_save.mode}") # Debug print

            # Ensure input is RGBA for rembg
            input_image = layer.pil_img_save
            if input_image.mode != 'RGBA':
                print(f"DEBUG: Converting input image to RGBA from {input_image.mode}") # Debug print
                input_image = input_image.convert("RGBA")

            # Use pil_img_save as input
            print("DEBUG: Calling rembg.remove()...") # Debug print
            removed_pil = remove(input_image)
            print(f"DEBUG: rembg.remove() finished. Output size: {removed_pil.size}, mode: {removed_pil.mode}") # Debug print

            tight_bbox = removed_pil.getbbox()
            print(f"DEBUG: BBox after rembg: {tight_bbox}") # Debug print

            final_pil = removed_pil.crop(tight_bbox) if tight_bbox else removed_pil
            if final_pil.width == 0 or final_pil.height == 0:
                print(f"Warning: Background removal resulted in empty image for {layer.path}. Using uncropped.") # Debug print
                final_pil = removed_pil # Fallback to uncropped if bbox is invalid
            print(f"DEBUG: Final PIL image size after crop: {final_pil.size}, mode: {final_pil.mode}") # Debug print

            # [ ★★★★★ 수정 2: 배경 제거된 이미지로 save/display 이미지 업데이트 ★★★★★ ]
            layer.pil_img_save = final_pil.copy()
            layer.pil_img_save.thumbnail(SAVE_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
            print(f"DEBUG: Updated pil_img_save size: {layer.pil_img_save.size}") # Debug print

            layer.pil_img_display = layer.pil_img_save.copy()
            layer.pil_img_display.thumbnail(DISPLAY_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
            print(f"DEBUG: Updated pil_img_display size: {layer.pil_img_display.size}") # Debug print

            layer.crop_box = None
            layer.angle = 0.0
            
            # [ ★★★★★ NEW: 배경 제거 후 content_bbox 업데이트 호출 ★★★★★ ]
            layer._update_content_bbox() 
            
            # Thumbnail 업데이트는 bbox 업데이트 이후에 수행
            layer.thumbnail = layer.create_thumbnail()
            layer._thumbnail_ref = layer.thumbnail
            print(f"DEBUG: Reset crop_box, angle, updated bbox and thumbnail.") # Debug print

            print(f"--- DEBUG: remove_background END for {layer.path} (Success) ---") # Debug print
            return True

        except Exception as e:
            print(f"ERROR during background removal for {layer.path}: {e}") # Debug print
            traceback.print_exc() # Print detailed traceback
            messagebox.showerror("배경 제거 오류", f"배경 제거 중 오류가 발생했습니다: {e}")
            print(f"--- DEBUG: remove_background END for {layer.path} (Failed: Exception) ---") # Debug print
            return False
    # [ ★★★★★ 수정된 함수 끝 ★★★★★ ]

    @staticmethod
    def _rotate_points(points, center, angle_degrees):
        angle_rad = math.radians(angle_degrees); cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad); cx, cy = center; new_points = []
        for i in range(0, len(points), 2):
            px, py = points[i], points[i+1]; px_rel, py_rel = px - cx, py - cy
            new_px = px_rel * cos_a - py_rel * sin_a + cx; new_py = px_rel * sin_a + py_rel * cos_a + cy; new_points.extend([new_px, new_py])
        return new_points