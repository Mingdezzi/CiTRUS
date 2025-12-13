import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def find_python_files(root_dir, exclude_self=True):
    """모든 .py 파일 찾기"""
    py_files = []
    current_script = os.path.abspath(__file__)
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                # 자기 자신 제외
                if exclude_self and os.path.abspath(filepath) == current_script:
                    continue
                py_files.append(filepath)
    return sorted(py_files)

def build_tree_structure(py_files, root_dir):
    """트리 구조 생성"""
    tree = defaultdict(list)
    
    for filepath in py_files:
        dir_path = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        tree[dir_path].append(filename)
    
    return tree

def get_relative_parts(path, root):
    """상대 경로를 부분별로 반환"""
    rel_path = os.path.relpath(path, root)
    if rel_path == '.':
        return []
    return rel_path.split(os.sep)

def print_tree(tree, root_dir, output_file, py_files):
    """트리 형태로 출력하고 각 파일의 코드도 추가"""
    with open(output_file, 'w', encoding='utf-8') as f:
        # 헤더
        f.write("=" * 80 + "\n")
        f.write("Python 프로젝트 분석 결과\n")
        f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # (1) 프로젝트 파일 구조
        f.write("(1) 프로젝트 파일 구조\n")
        f.write("-" * 80 + "\n\n")
        
        # 루트 디렉토리
        f.write(f"{root_dir}\n")
        
        # 디렉토리별로 정렬
        sorted_dirs = sorted(tree.keys())
        
        # 디렉토리 구조를 계층적으로 표시
        processed_parts = set()
        
        for dir_path in sorted_dirs:
            parts = get_relative_parts(dir_path, root_dir)
            
            # 각 부분 디렉토리 출력
            for i, part in enumerate(parts):
                current_path = os.sep.join(parts[:i+1])
                
                if current_path not in processed_parts:
                    indent = "│   " * i
                    f.write(f"{indent}├── [{part}]\n")
                    processed_parts.add(current_path)
            
            # 파일 출력
            indent = "│   " * len(parts)
            for filename in sorted(tree[dir_path]):
                f.write(f"{indent}│   ├── {filename}\n")
        
        # 통계
        total_files = sum(len(files) for files in tree.values())
        f.write("\n" + "-" * 80 + "\n")
        f.write(f"총 Python 파일 개수: {total_files}개\n")
        f.write(f"총 디렉토리 개수: {len(tree)}개\n")
        f.write(f"※ 이 스크립트 파일({os.path.basename(__file__)})은 결과에서 제외되었습니다.\n")
        f.write("\n\n")
        
        # (2) 각 파일의 코드 내용
        f.write("=" * 80 + "\n")
        f.write("(2) 각 파일의 코드 내용\n")
        f.write("=" * 80 + "\n\n")
        
        for index, filepath in enumerate(py_files, start=2):
            relative_path = os.path.relpath(filepath, root_dir)
            filename = os.path.basename(filepath)
            
            f.write(f"({index}) {relative_path}\n")
            f.write("-" * 80 + "\n")
            
            # 파일 내용 읽기
            try:
                with open(filepath, 'r', encoding='utf-8') as code_file:
                    code_content = code_file.read()
                    f.write(code_content)
                    
                    # 파일 끝에 줄바꿈이 없으면 추가
                    if code_content and not code_content.endswith('\n'):
                        f.write('\n')
                        
            except Exception as e:
                f.write(f"[오류: 파일을 읽을 수 없습니다 - {str(e)}]\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
        
    return total_files

def main():
    # 스크립트 파일이 위치한 디렉토리를 기준으로
    root_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(root_dir, "python_file_tree.txt")
    
    print("Python 파일 트리 구조를 생성중입니다...")
    print()
    
    # Python 파일 찾기
    py_files = find_python_files(root_dir)
    
    if not py_files:
        print("현재 디렉토리 및 하위 디렉토리에서 Python 파일을 찾을 수 없습니다.")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Python 파일을 찾을 수 없습니다.\n")
        return
    
    # 트리 구조 생성
    tree = build_tree_structure(py_files, root_dir)
    
    # 파일로 출력 (트리 + 코드 내용)
    total_files = print_tree(tree, root_dir, output_file, py_files)
    
    print(f"완료! Python 파일 트리 및 코드가 '{output_file}' 파일에 저장되었습니다.")
    print(f"총 {total_files}개의 Python 파일을 발견했습니다.")
    print()
    
    # 결과 파일 열기 옵션
    response = input("결과 파일을 여시겠습니까? (Y/N): ").strip().upper()
    if response == 'Y':
        os.startfile(output_file)

if __name__ == "__main__":
    main()