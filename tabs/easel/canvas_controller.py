import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math
import os

from .models.layer import Layer, ImageLayer, TextLayer, ShapeLayer
from .services.font_service import FontService
from .services.image_service import ImageService

class CanvasController:
    def __init__(self, canvas: tk.Canvas, controller):
        self.canvas = canvas
        self.controller = controller
        self.canvas_objects = {}
        self.active_selection_path: str | None = None
        self.fit_scale = 1.0

    def add_layer_to_canvas(self, layer: Layer):
        if layer.path in self.canvas_objects:
            return

        canvas_w, canvas_h = self.get_canvas_size()
        center_x, center_y = canvas_w / 2, canvas_h / 2

        item_id = self.canvas.create_image(center_x, center_y, tags=("item", layer.path))

        self.canvas_objects[layer.path] = {
            'id': item_id,
            'type': layer.type,
            'tk_img': None,
            'pil_for_display': None,
            'rel_x': 0.5,
            'rel_y': 0.5,
            'angle': layer.angle
        }
        
        if isinstance(layer, ShapeLayer):
            self.canvas_objects[layer.path].update({
                'shape_type': layer.shape_type,
                'color': layer.color,
                'pil_image': layer.pil_image
            })

        self.update_object_display(layer, self.controller.get_zoom())
        self.reorder_canvas_layers()

    def remove_layer_from_canvas(self, layer: Layer):
        if layer.path in self.canvas_objects:
            item_id = self.canvas_objects[layer.path]['id']
            self.canvas.delete(item_id)
            del self.canvas_objects[layer.path]
            if self.active_selection_path == layer.path:
                self.clear_resize_handles()

    def update_object_display(self, layer_or_logo: Layer | dict, zoom: float):
        is_logo = isinstance(layer_or_logo, dict) and layer_or_logo.get('type') == 'logo'
        path = layer_or_logo.get('path') if is_logo else layer_or_logo.path

        if path not in self.canvas_objects and not is_logo:
             return

        obj_info = self.controller.logo_object if is_logo else self.canvas_objects[path]
        item_id = obj_info['id']

        canvas_w, canvas_h = self.get_canvas_size(zoom)
        if canvas_w <= 1 : return

        actual_zoom = self.fit_scale * zoom

        pil_img = None
        if is_logo:
             pil_img = self.controller._get_display_pil_for_logo(actual_zoom)
        else:
             pil_img = self._get_display_pil_for_layer(layer_or_logo, actual_zoom)

        if pil_img is None:
             self.canvas.itemconfig(item_id, state='hidden')
             return
        else:
             self.canvas.itemconfig(item_id, state='normal')

        obj_info['tk_img'] = ImageTk.PhotoImage(pil_img)
        obj_info['pil_for_display'] = pil_img
        self.canvas.itemconfig(item_id, image=obj_info['tk_img'])

        x = obj_info['rel_x'] * canvas_w
        y = obj_info['rel_y'] * canvas_h
        self.canvas.coords(item_id, x, y)

        if self.active_selection_path == path:
             self.activate_resize_handles(path)

    def _get_display_pil_for_layer(self, layer: Layer, actual_zoom: float) -> Image.Image | None:
        img = None
        target_w, target_h = 0, 0
        original_pil = None

        if isinstance(layer, ImageLayer):
            original_pil = layer.get_pil_image_to_process()
            content_w, content_h = layer.get_content_dimensions()
            
            canvas_h_logical = self.controller.settings['output_height'].get()
            logo_zone_h_logical = canvas_h_logical * (self.controller.settings['logo_zone_height'].get() / 1500.0)
            
            target_h_logical = (canvas_h_logical - logo_zone_h_logical) * (layer.scale_var.get() / 100.0)

            if content_h > 0:
                ratio = target_h_logical / content_h
                target_w = int(original_pil.width * ratio * actual_zoom)
                target_h = int(original_pil.height * ratio * actual_zoom)
            else:
                 return None

        elif isinstance(layer, TextLayer):
            try:
                font_size = int(layer.scale_var.get() * actual_zoom)
                if font_size < 1: return None
                font = ImageFont.truetype(FontService.get_font_path(layer.font_family), font_size)
                
                bbox = font.getbbox(layer.text)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                if text_w <= 0 or text_h <= 0: return None

                img = Image.new('RGBA', (text_w, text_h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.text((-bbox[0], -bbox[1]), layer.text, font=font, fill=layer.color)
                original_pil = img

            except Exception:
                return None

        elif isinstance(layer, ShapeLayer):
            if layer.shape_type == '자유곡선':
                original_pil = layer.pil_image
                if original_pil:
                     scale_factor = layer.scale_var.get() / 100.0
                     target_w = int(original_pil.width * scale_factor * actual_zoom)
                     target_h = int(original_pil.height * scale_factor * actual_zoom)
                else: return None
            else:
                 size = layer.scale_var.get() * actual_zoom
                 if size < 1: return None
                 points = layer._get_shape_points((0, 0), size)
                 if not points: return None

                 if layer.angle != 0:
                    points = ImageService._rotate_points(points, (0, 0), -layer.angle)

                 xs, ys = zip(*[(points[i], points[i+1]) for i in range(0, len(points), 2)])
                 min_x, max_x = min(xs), max(xs)
                 min_y, max_y = min(ys), max(ys)
                 width, height = int(max_x - min_x) + 1, int(max_y - min_y) + 1
                 if width <= 0 or height <= 0: return None

                 img = Image.new('RGBA', (width, height), (0,0,0,0))
                 shape_draw = ImageDraw.Draw(img)
                 shifted_points = [(x - min_x, y - min_y) for x, y in zip(xs, ys)]
                 shape_draw.polygon(shifted_points, fill=layer.color)
                 return img

        if original_pil is None: return None
        
        if isinstance(layer, TextLayer):
            if layer.angle != 0:
                return original_pil.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)
            else:
                return original_pil
        
        if target_w < 1 or target_h < 1: return None

        try:
            resized_img = original_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
            if layer.angle != 0:
                return resized_img.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)
            else:
                return resized_img
        except Exception:
            return None

    def update_all_objects_display(self, zoom: float):
        for layer in self.controller.get_layers():
            if layer.is_visible.get():
                self.update_object_display(layer, zoom)
        if self.controller.logo_object:
            self.update_object_display(self.controller.logo_object, zoom)

    def reorder_canvas_layers(self):
        if self.controller.logo_object:
             self.canvas.lift(self.controller.logo_object['id'])

        for layer in reversed(self.controller.get_layers()):
            if layer.path in self.canvas_objects:
                self.canvas.lift(self.canvas_objects[layer.path]['id'])

    def get_canvas_size(self, zoom: float = None) -> tuple[int, int]:
        if zoom is None: zoom = self.controller.get_zoom()
        w = int(self.controller.settings['output_width'].get() * self.fit_scale * zoom)
        h = int(self.controller.settings['output_height'].get() * self.fit_scale * zoom)
        return max(1, w), max(1, h)

    def finalize_object_move(self, path: str):
        obj_info = None
        if path == 'logo':
             obj_info = self.controller.logo_object
        elif path in self.canvas_objects:
             obj_info = self.canvas_objects[path]

        if not obj_info: return

        canvas_w, canvas_h = self.get_canvas_size()
        item_id = obj_info['id']
        coords = self.canvas.coords(item_id)

        img_w, img_h = 0, 0
        pil_img = obj_info.get('pil_for_display')
        if pil_img:
             img_w, img_h = pil_img.width, pil_img.height

        logo_zone_h = canvas_h * (self.controller.settings['logo_zone_height'].get() / 1500.0)
        current_zoom = self.controller.get_zoom()
        current_canvas_w, current_canvas_h = self.get_canvas_size(current_zoom)
        current_logo_zone_h = current_canvas_h * (self.controller.settings['logo_zone_height'].get() / 1500.0)

        current_min_y = current_logo_zone_h + img_h / 2 if path != 'logo' else img_h / 2
        current_max_y = current_canvas_h - img_h / 2
        current_min_x = img_w / 2
        current_max_x = current_canvas_w - img_w / 2

        final_x = max(current_min_x, min(coords[0], current_max_x))
        final_y = max(current_min_y, min(coords[1], current_max_y))

        if coords[0] != final_x or coords[1] != final_y:
            self.canvas.coords(item_id, final_x, final_y)

        obj_info['rel_x'] = final_x / current_canvas_w if current_canvas_w > 0 else 0.5
        obj_info['rel_y'] = final_y / current_canvas_h if current_canvas_h > 0 else 0.5

    def activate_resize_handles(self, path: str):
        self.clear_resize_handles()
        self.active_selection_path = path

        obj_info = None
        if path == 'logo':
             obj_info = self.controller.logo_object
        elif path in self.canvas_objects:
             obj_info = self.canvas_objects[path]

        if not obj_info or 'id' not in obj_info:
             self.active_selection_path = None
             return

        item_id = obj_info['id']
        pil_img = obj_info.get('pil_for_display')
        if not pil_img:
             self.active_selection_path = None
             return

        angle_degrees = obj_info.get('angle', 0.0)
        angle_rad = math.radians(angle_degrees)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)

        cx, cy = self.canvas.coords(item_id)
        w, h = pil_img.width, pil_img.height
        hw, hh = w / 2, h / 2

        handle_positions = {
            'nw': (-hw, -hh), 'n': (0, -hh), 'ne': (hw, -hh),
            'w':  (-hw, 0),                 'e':  (hw, 0),
            'sw': (-hw, hh), 's': (0, hh), 'se': (hw, hh)
        }
        handle_size = 6

        corners = [
            handle_positions['nw'], handle_positions['ne'],
            handle_positions['se'], handle_positions['sw']
        ]
        rotated_corners = []
        for rel_x, rel_y in corners:
            rot_x = rel_x * cos_a - rel_y * sin_a
            rot_y = rel_x * sin_a + rel_y * cos_a
            rotated_corners.extend([cx + rot_x, cy + rot_y])

        self.canvas.create_polygon(rotated_corners, fill='', outline='blue', width=1, tags=('border', path))

        if path != 'logo':
            for name, (rel_x, rel_y) in handle_positions.items():
                rot_x = rel_x * cos_a - rel_y * sin_a
                rot_y = rel_x * sin_a + rel_y * cos_a
                abs_x, abs_y = cx + rot_x, cy + rot_y
                self.canvas.create_rectangle(
                    abs_x - handle_size/2, abs_y - handle_size/2,
                    abs_x + handle_size/2, abs_y + handle_size/2,
                    fill='white', outline='blue', width=1, tags=('handle', name, path)
                )

            rotate_handle_y_offset = -hh - 20
            rot_x = 0 * cos_a - rotate_handle_y_offset * sin_a
            rot_y = 0 * sin_a + rotate_handle_y_offset * cos_a
            abs_x, abs_y = cx + rot_x, cy + rot_y
            self.canvas.create_oval(
                abs_x - handle_size/2, abs_y - handle_size/2,
                abs_x + handle_size/2, abs_y + handle_size/2,
                fill='lightblue', outline='blue', width=1, tags=('rotate_handle', path)
            )

        self.reorder_canvas_layers()

    def clear_resize_handles(self):
        self.canvas.delete("handle")
        self.canvas.delete("rotate_handle")
        self.canvas.delete("border")
        self.active_selection_path = None

    def process_resizing(self, current_x, current_y, resize_data):
        if not resize_data: return

        item_id = resize_data['item_id']
        handle_type = resize_data['handle_type']
        start_x, start_y = resize_data['start_x'], resize_data['start_y']
        start_bbox = resize_data['start_bbox']

        path = self.active_selection_path
        if not path or path == 'logo': return
        layer = self.controller.get_layer_by_path(path)
        if not layer: return

        obj_info = self.canvas_objects.get(path)
        if not obj_info: return

        cx, cy = self.canvas.coords(item_id)

        angle_degrees = obj_info.get('angle', 0.0)
        angle_rad = math.radians(angle_degrees)
        cos_a_inv, sin_a_inv = math.cos(-angle_rad), math.sin(-angle_rad)

        start_x_rel, start_y_rel = start_x - cx, start_y - cy
        current_x_rel, current_y_rel = current_x - cx, current_y - cy

        unrot_start_x = start_x_rel * cos_a_inv - start_y_rel * sin_a_inv
        unrot_start_y = start_x_rel * sin_a_inv + start_y_rel * cos_a_inv
        unrot_current_x = current_x_rel * cos_a_inv - current_y_rel * sin_a_inv
        unrot_current_y = current_x_rel * sin_a_inv + current_y_rel * cos_a_inv

        unrot_dx = unrot_current_x - unrot_start_x
        unrot_dy = unrot_current_y - unrot_start_y

        start_w = start_bbox[2] - start_bbox[0]
        start_h = start_bbox[3] - start_bbox[1]

        new_w, new_h = start_w, start_h
        aspect_ratio = start_w / start_h if start_h != 0 else 1.0

        if 'n' in handle_type:
             new_h = start_h - unrot_dy
             if 'w' not in handle_type and 'e' not in handle_type: new_w = new_h * aspect_ratio
        if 's' in handle_type:
             new_h = start_h + unrot_dy
             if 'w' not in handle_type and 'e' not in handle_type: new_w = new_h * aspect_ratio
        if 'w' in handle_type:
             new_w = start_w - unrot_dx
             if 'n' not in handle_type and 's' not in handle_type: new_h = new_w / aspect_ratio
        if 'e' in handle_type:
             new_w = start_w + unrot_dx
             if 'n' not in handle_type and 's' not in handle_type: new_h = new_w / aspect_ratio

        min_size = 10
        new_w = max(min_size, new_w)
        new_h = max(min_size, new_h)

        if start_w > 0 and start_h > 0:
            if isinstance(layer, ImageLayer):
                if 'w' in handle_type or 'e' in handle_type:
                     scale_change = new_w / start_w
                else:
                     scale_change = new_h / start_h
                
                new_scale = layer.scale_var.get() * scale_change
                layer.scale_var.set(max(1.0, new_scale))

            elif isinstance(layer, (TextLayer, ShapeLayer)):
                 scale_change = max(new_w / start_w, new_h / start_h)
                 new_scale = layer.scale_var.get() * scale_change
                 layer.scale_var.set(max(1.0, new_scale))

        resize_data.update(start_x=current_x, start_y=current_y)

    def process_rotation(self, current_x, current_y, rotation_data):
        if not rotation_data: return
        cx, cy = rotation_data['center_x'], rotation_data['center_y']
        start_angle = rotation_data['start_angle']
        initial_item_angle = rotation_data['initial_item_angle']

        current_angle = math.degrees(math.atan2(current_y - cy, current_x - cx))
        delta_angle = current_angle - start_angle
        new_angle = (initial_item_angle + delta_angle) % 360

        path = self.active_selection_path
        if path and path != 'logo':
            layer = self.controller.get_layer_by_path(path)
            if layer:
                layer.angle = new_angle
                if path in self.canvas_objects:
                     self.canvas_objects[path]['angle'] = new_angle
                self.update_object_display(layer, self.controller.get_zoom())

    def finalize_resize_or_rotate(self, path: str):
        if not path or path == 'logo': return
        layer = self.controller.get_layer_by_path(path)
        if layer:
            self.update_object_display(layer, self.controller.get_zoom())
            self.controller.update_status(f"'{layer.get_display_name()}' 변형 완료.")
        self.activate_resize_handles(path)

    def get_object_info_by_id(self, item_id: int) -> dict | None:
        if self.controller.logo_object and self.controller.logo_object.get('id') == item_id:
            return self.controller.logo_object
        for info in self.canvas_objects.values():
            if info.get('id') == item_id:
                return info
        return None