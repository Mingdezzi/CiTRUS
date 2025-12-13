from supabase import create_client, Client
# --- 여기가 수정된 부분 ---
# 내부 모듈/오류 직접 임포트 제거 (다시!)
# --- 수정 끝 ---
import os

# --- Supabase URL/Key 설정 (기존과 동일) ---
SUPABASE_URL = "https://fhqlmbmlcfpaizodrmxc.supabase.co" # <<< 본인 URL 확인!
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZocWxtYm1sY2ZwYWl6b2RybXhjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA3Mjk2MDcsImV4cCI6MjA3NjMwNTYwN30.AVLHGuiGHHBEW5TCXMeDar8y9N5GCsYewMbfZR1JGcM" # <<< 본인 Key 확인!
# -----------------------------------------------

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"DEBUG: Supabase 클라이언트 초기화 성공. URL: {SUPABASE_URL}")
except Exception as e:
    print(f"DEBUG: Supabase 클라이언트 초기화 실패: {e}")
    supabase = None

def initialize_database():
    if supabase is None:
        print("오류: Supabase가 초기화되지 않았습니다. URL과 KEY를 확인하세요.")
        return
    print("DEBUG: Supabase 사용 중 (로컬 DB 초기화 건너뜀).")

def create_user(name, username, email, password):
    """
    회원가입 처리: Supabase Auth에 사용자를 생성하고, profiles 테이블에 추가 정보를 저장합니다.
    성공 시: True, 실패 시: (오류 메시지 문자열)
    """
    if supabase is None: return "Supabase 연결 실패"

    user_id = None
    try:
        # 1. Supabase Auth에 이메일/비밀번호로 사용자 생성
        user_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": { "name": name }
            }
        })
        user_id = user_response.user.id
        print(f"DEBUG: Supabase Auth 사용자 생성 성공: {email} (ID: {user_id})")

        # 2. profiles 테이블에 username, name, email 추가 (role은 DB 기본값 1 사용)
        profile_data = supabase.table('profiles').insert({
            'id': str(user_id),
            'username': username,
            'name': name,
            'email': email
        }).execute()

        if profile_data.data:
             print(f"DEBUG: Supabase profiles 테이블에 정보 추가 완료: {username}")
        else:
             print(f"경고: profiles 테이블 insert 후 반환 데이터 없음. {getattr(profile_data, 'error', 'N/A')}")

        return True

    # --- 오류 처리 방식 (Exception으로 통일) ---
    except Exception as e:
        err_msg = str(getattr(e, 'message', str(e))).lower()
        print(f"DEBUG: 회원가입 중 오류 발생: {err_msg}") # 오류 메시지 직접 확인

        # Auth 관련 오류 메시지 패턴 확인
        if "user already exists" in err_msg or "already registered" in err_msg:
             return "duplicate_email"
        elif "valid email" in err_msg:
            return "invalid_email"
        elif "characters long" in err_msg or "password should be" in err_msg:
             return "password_too_short"

        # DB 관련 오류 메시지 패턴 확인 (Postgrest)
        elif "duplicate key value violates unique constraint" in err_msg and "profiles_username_key" in err_msg:
             if user_id: # 롤백 시도
                 print(f"롤백 시도: Auth 사용자 삭제 {user_id}")
                 try:
                     # supabase.auth.admin.delete_user(user_id) # 관리자 권한 필요
                     print("경고: Auth 사용자 롤백 실패 (관리자 권한 필요)")
                 except Exception as admin_e:
                     print(f"Auth 사용자 롤백 중 오류: {admin_e}")
             return "duplicate_username"
        elif "postgrest" in err_msg or "database" in err_msg:
             return f"DB 오류: {e}"

        # 기타 알 수 없는 오류
        return f"알 수 없는 오류: {e}"
    # --- 수정 끝 ---

def check_user_login(username, password):
    """
    로그인 처리: username으로 email을 찾고, email/password로 로그인 후 role 숫자를 반환합니다.
    성공 시: role 숫자 (e.g., 1, 2), 실패 시: None
    """
    if supabase is None: return None

    try:
        # 1. profiles 테이블에서 username으로 email과 role 조회
        print(f"DEBUG: profiles 테이블에서 username '{username}' 조회 시도...")
        profile_response = supabase.table('profiles').select('id, email, role').eq('username', username).execute()

        if not profile_response.data:
            print(f"DEBUG: 로그인 실패 (존재하지 않는 아이디: {username})")
            return None # 아이디 없음

        profile = profile_response.data[0]
        user_id = profile['id']
        email = profile['email']
        role_number = profile['role']
        print(f"DEBUG: 아이디 '{username}'에 해당하는 이메일 '{email}', 역할(숫자) '{role_number}' 찾음.")

        # 2. 찾은 email과 입력된 password로 Supabase Auth 로그인 시도
        print(f"DEBUG: Supabase Auth 로그인 시도 (이메일: {email})...")
        session = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        # 3. 로그인 성공 시 역할(role) 숫자 반환
        print(f"DEBUG: Supabase 로그인 성공: {session.user.email}")
        return role_number # 숫자 반환

    # --- 오류 처리 방식 (Exception으로 통일) ---
    except Exception as e:
        err_msg = str(getattr(e, 'message', str(e))).lower()
        print(f"DEBUG: 로그인 중 오류 발생: {err_msg}") # 오류 메시지 직접 확인

        # Auth 관련 오류 메시지 패턴 확인 ("Invalid login credentials" 등)
        if "invalid login credentials" in err_msg:
            print("DEBUG: 로그인 실패 (Auth: 자격 증명 오류)")
            return None
        # DB 관련 오류 메시지 패턴 확인
        elif "postgrest" in err_msg or "table" in err_msg or "database" in err_msg:
            print(f"DEBUG: 로그인 실패 (DB 조회 오류)")
            return None
        # 기타 알 수 없는 오류
        else:
            print(f"DEBUG: 로그인 실패 (알 수 없는 오류)")
            return None
    # --- 수정 끝 ---
