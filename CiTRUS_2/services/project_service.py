# 파일 경로: services/project_service.py (이 코드로 완전히 교체하세요)

import pickle
from tkinter import filedialog, messagebox
import os
from models.layer import Layer, ImageLayer, TextLayer, ShapeLayer

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
            
            # --- 설정 키 이름 호환 (구버전 'global_settings' -> 신버전 'settings') ---
            if 'global_settings' in project_data and 'settings' not in project_data:
                project_data['settings'] = project_data.pop('global_settings')

            # 레이어 객체 재구성
            deserialized_layers = []
            for layer_data in project_data.get('layers', []):
                layer = ProjectService._deserialize_layer(layer_data) # 수정된 함수 호출
                if layer:
                    deserialized_layers.append(layer)
            project_data['layers'] = deserialized_layers

            messagebox.showinfo("성공", "프로젝트를 성공적으로 불러왔습니다.")
            return project_data
            
        except Exception as e:
            messagebox.showerror("불러오기 오류", f"프로젝트 파일을 불러오는 중 오류가 발생했습니다:\n{e}")
            return None
            
    @staticmethod
    def _serialize_layer(layer: Layer) -> dict:
        """Layer 객체를 저장 가능한 딕셔너리로 변환"""
        data = {
            '__class__': layer.__class__.__name__,
            'type': layer.type,
            'path': layer.path,
            'is_visible': layer.is_visible.get(),
            'angle': layer.angle,
            'scale': layer.scale_var.get(),
        }
        if isinstance(layer, ImageLayer):
            # PIL 이미지는 직접 저장하지 않고, 로드 시 경로를 통해 다시 생성
            data.update({
                'crop_box': layer.crop_box,
            })
        elif isinstance(layer, TextLayer):
            data.update({
                'text': layer.text,
                'font_family': layer.font_family,
                'color': layer.color,
            })
        elif isinstance(layer, ShapeLayer):
            data.update({
                'shape_type': layer.shape_type,
                'color': layer.color,
                'pil_image': layer.pil_image, # 자유곡선 이미지
            })
        return data

    # --- 여기가 핵심 수정 부분 ---
    @staticmethod
    def _deserialize_layer(data: dict) -> Layer | None:
        """딕셔너리로부터 Layer 객체를 복원 (이전 버전 호환)"""
        
        class_name = None
        # 1. __class__ 키가 있는지 확인 (신규 버전)
        if '__class__' in data:
            class_name = data.pop('__class__')
        # 2. 없다면 'type' 키로 유추 (구버전)
        elif 'type' in data:
            type_name = data.get('type')
            if type_name == 'image':
                class_name = 'ImageLayer'
            elif type_name == 'text':
                class_name = 'TextLayer'
            elif type_name == 'shape':
                class_name = 'ShapeLayer'
            else:
                print(f"알 수 없는 구버전 레이어 타입: {type_name}")
                return None
        # 3. 둘 다 없으면 로드 실패
        else:
            print(f"필수 키('__class__' 또는 'type')가 없는 레이어 데이터입니다.")
            return None

        layer = None
        try:
            if class_name == 'ImageLayer':
                # 구버전은 'path'가 없을 수 있음 (매우 초기 버전)
                # 하지만 현재 리팩토링 직전 버전은 'path'가 있었음
                if 'path' not in data:
                    print(f"ImageLayer에 'path' 키가 없습니다.")
                    return None
                layer = ImageLayer(data['path'])
                layer.crop_box = data.get('crop_box')

            elif class_name == 'TextLayer':
                # 구버전은 font_size를 scale_var_value에 저장
                font_size = data.get('scale', data.get('scale_var_value', 30))
                layer = TextLayer(data['text'], data['font_family'], font_size, data['color'])

            elif class_name == 'ShapeLayer':
                # 구버전은 pil_image를 저장했음 (pil_img_save는 이미지 레이어용)
                pil_image = data.get('pil_image') 
                layer = ShapeLayer(data['shape_type'], data['color'], pil_image)

        except Exception as e:
            print(f"레이어 객체 생성 실패({data.get('path', 'N/A')}): {e}. 건너뜁니다.")
            return None

        if layer:
            # 구버전은 'var_value', 신버전은 'is_visible'
            is_visible = data.get('is_visible', data.get('var_value', False))
            layer.is_visible.set(is_visible)
            
            layer.angle = data.get('angle', 0.0)
            
            # 구버전은 'scale_var_value', 신버전은 'scale'
            default_scale = 30.0 if class_name == 'ImageLayer' else 100.0
            scale = data.get('scale', data.get('scale_var_value', default_scale))
            layer.scale_var.set(scale)
            
        return layer
    # --- 수정 끝 ---

    @staticmethod
    def _serialize_canvas_positions(canvas_objects: dict) -> dict:
        """캔버스 객체들의 상대 좌표를 저장"""
        positions = {}
        for path, obj_info in canvas_objects.items():
            positions[path] = {'rel_x': obj_info['rel_x'], 'rel_y': obj_info['rel_y']}
        return positions