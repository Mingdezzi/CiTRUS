import pickle
from tkinter import filedialog, messagebox
import os
# --- import 경로 수정 (상대 경로 사용) ---
from ..models.layer import Layer, ImageLayer, TextLayer, ShapeLayer
# --- 수정 끝 ---

class ProjectService:
    """프로젝트 저장 및 불러오기 기능을 담당하는 서비스 클래스"""

    @staticmethod
    def save_project(settings: dict, layers: list[Layer], canvas_objects: dict):
        path = filedialog.asksaveasfilename(
            title="프로젝트 저장",
            defaultextension=".wsb",
            filetypes=[("CiTRUS Project", "*.wsb")]
        )
        if not path:
            return

        try:
            project_data = {
                'settings': settings,
                'layers': [ProjectService._serialize_layer(l) for l in layers],
                'canvas_positions': ProjectService._serialize_canvas_positions(canvas_objects)
            }
            with open(path, 'wb') as f:
                pickle.dump(project_data, f)

            messagebox.showinfo("성공", "프로젝트를 성공적으로 저장했습니다.")
            return f"프로젝트 저장 완료: {os.path.basename(path)}"
        except Exception as e:
            messagebox.showerror("저장 오류", f"프로젝트 저장 중 오류가 발생했습니다:\n{e}")
            return "프로젝트 저장 실패."

    @staticmethod
    def load_project():
        path = filedialog.askopenfilename(
            title="프로젝트 불러오기",
            filetypes=[("CiTRUS Project", "*.wsb")]
        )
        if not path:
            return None

        try:
            with open(path, 'rb') as f:
                project_data = pickle.load(f)

            if 'global_settings' in project_data and 'settings' not in project_data:
                project_data['settings'] = project_data.pop('global_settings')

            deserialized_layers = []
            for layer_data in project_data.get('layers', []):
                layer = ProjectService._deserialize_layer(layer_data)
                if layer:
                    deserialized_layers.append(layer)
            project_data['layers'] = deserialized_layers
            project_data['path'] = path

            messagebox.showinfo("성공", "프로젝트를 성공적으로 불러왔습니다.")
            return project_data

        except Exception as e:
            messagebox.showerror("불러오기 오류", f"프로젝트 파일을 불러오는 중 오류가 발생했습니다:\n{e}")
            return None

    @staticmethod
    def _serialize_layer(layer: Layer) -> dict:
        data = {
            '__class__': layer.__class__.__name__,
            'type': layer.type,
            'path': layer.path,
            'is_visible': layer.is_visible.get(),
            'angle': layer.angle,
            'scale': layer.scale_var.get(),
        }
        if isinstance(layer, ImageLayer):
            data.update({'crop_box': layer.crop_box})
        elif isinstance(layer, TextLayer):
            data.update({'text': layer.text, 'font_family': layer.font_family, 'color': layer.color})
        elif isinstance(layer, ShapeLayer):
            data.update({'shape_type': layer.shape_type, 'color': layer.color, 'pil_image': layer.pil_image})
        return data

    @staticmethod
    def _deserialize_layer(data: dict) -> Layer | None:
        class_name = None
        if '__class__' in data:
            class_name = data.pop('__class__')
        elif 'type' in data:
            type_name = data.get('type')
            if type_name == 'image': class_name = 'ImageLayer'
            elif type_name == 'text': class_name = 'TextLayer'
            elif type_name == 'shape': class_name = 'ShapeLayer'
            else: print(f"알 수 없는 구버전 레이어 타입: {type_name}"); return None
        else: print(f"필수 키('__class__' 또는 'type')가 없는 레이어 데이터입니다."); return None

        layer = None
        try:
            if class_name == 'ImageLayer':
                img_path = data.get('path')
                if not img_path: print(f"ImageLayer에 'path' 키가 없습니다."); return None
                normalized_path = os.path.normpath(img_path)
                if not os.path.exists(normalized_path):
                    messagebox.showwarning("파일 누락", f"이미지 파일을 찾을 수 없습니다:\n{normalized_path}")
                    return None
                layer = ImageLayer(normalized_path)
                layer.crop_box = data.get('crop_box')

            elif class_name == 'TextLayer':
                font_size = data.get('scale', data.get('scale_var_value', 30))
                layer = TextLayer(data['text'], data['font_family'], font_size, data['color'])

            elif class_name == 'ShapeLayer':
                pil_image = data.get('pil_image')
                layer = ShapeLayer(data['shape_type'], data['color'], pil_image)

        except Exception as e:
            print(f"레이어 객체 생성 실패({data.get('path', 'N/A')}): {e}. 건너뜁니다."); return None

        if layer:
            is_visible = data.get('is_visible', data.get('var_value', False))
            layer.is_visible.set(is_visible)
            layer.angle = data.get('angle', 0.0)
            default_scale = 30.0 if class_name == 'ImageLayer' else 100.0
            scale = data.get('scale', data.get('scale_var_value', default_scale))
            layer.scale_var.set(scale)

        return layer

    @staticmethod
    def _serialize_canvas_positions(canvas_objects: dict) -> dict:
        positions = {}
        for path, obj_info in canvas_objects.items():
            if obj_info and 'rel_x' in obj_info and 'rel_y' in obj_info:
                 positions[path] = {'rel_x': obj_info['rel_x'], 'rel_y': obj_info['rel_y']}
            else:
                 print(f"경고: 유효하지 않은 캔버스 객체 데이터 건너뜀 (path: {path})")
        return positions
