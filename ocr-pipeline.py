#!/usr/bin/env python3
"""
쿠폰 OCR 자동 처리 파이프라인

하는 일:
1. Google Drive 폴더에서 새 이미지 확인
2. OpenAI Vision API(GPT-4o)로 제품명/할인내용/유효기간 추출
3. Supabase Storage에 이미지 업로드
4. Supabase DB(coupons 테이블)에 쿠폰 정보 저장

사용법:
  python3 ocr-pipeline.py          # 전체 실행
  python3 ocr-pipeline.py --dry-run # 실제 저장 없이 분석만

환경변수:
  SUPABASE_URL, SUPABASE_ANON, SUPABASE_SVC (이미 설정됨)
  OPENAI_API_KEY (lecturenote .env에서 로드)
"""

import os, sys, json, base64, subprocess, re, datetime, time
import urllib.request, urllib.error

# ─── 설정 ───────────────────────────────────────────────
DRIVE_FOLDER_ID = "1SVCY7UjMOf2KQzxRF-LWxgksGgQ8EE3U"
GOG_ACCOUNT = "taejin@hanbit.co.kr"
STATE_FILE = os.path.expanduser(
    "~/Documents/github/coupon-manager/.processed_files.json"
)
GOG_DOWNLOAD_DIR = os.path.expanduser(
    "~/Library/Application Support/gogcli/drive-downloads"
)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

# ─── API 키 로드 ────────────────────────────────────────

def load_env_file(path):
    """.env 파일에서 KEY=VALUE 형식을 읽어 환경변수로 등록"""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

def normalize_loaded_keys():
    """기존 스크립트의 변수명을 파이프라인 표준 환경변수명으로 맞춤"""
    if not os.environ.get("SUPABASE_SVC") and os.environ.get("SERVICE_KEY"):
        os.environ["SUPABASE_SVC"] = os.environ["SERVICE_KEY"]
    if not os.environ.get("SUPABASE_ANON") and os.environ.get("SUPABASE_ANON_KEY"):
        os.environ["SUPABASE_ANON"] = os.environ["SUPABASE_ANON_KEY"]


def get_supabase_keys():
    """환경변수/프로젝트 스크립트에서 Supabase 키 읽기"""
    normalize_loaded_keys()
    url = os.environ.get("SUPABASE_URL", "")
    anon = os.environ.get("SUPABASE_ANON", "")
    svc = os.environ.get("SUPABASE_SVC", "")
    return url, anon, svc

def get_openai_key():
    """환경변수에서 OpenAI 키 읽기 (lecturenote .env 사전 로드)"""
    return os.environ.get("OPENAI_API_KEY", "")

# ─── Google Drive ───────────────────────────────────────

def _run_gog(args, timeout=30):
    """gog CLI 호출 — cron 등 PATH가 비어있는 환경에서도 동작하도록 보강"""
    env = os.environ.copy()
    env.setdefault("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
    return subprocess.run(["gog", *args], capture_output=True, text=True, timeout=timeout, env=env)


def drive_list_files(folder_id):
    """gog CLI로 Drive 폴더 내 파일 목록 조회"""
    result = _run_gog(["drive", "ls",
                       "--account", GOG_ACCOUNT,
                       "--parent", folder_id,
                       "-j"], timeout=30)
    if result.returncode != 0:
        print(f"[오류] Drive 폴더 조회 실패: {result.stderr}")
        return []
    try:
        data = json.loads(result.stdout)
        return data.get("files", [])
    except json.JSONDecodeError:
        print(f"[오류] JSON 파싱 실패")
        return []

def drive_download(file_id, filename):
    """gog CLI로 파일 다운로드, 로컬 경로 반환"""
    target_path = os.path.join(GOG_DOWNLOAD_DIR, f"{file_id}_{filename}")
    if os.path.exists(target_path):
        print(f"  이미 다운로드됨: {target_path}")
        return target_path

    result = _run_gog(["drive", "download",
                       "--account", GOG_ACCOUNT,
                       file_id], timeout=60)
    if result.returncode != 0:
        print(f"  [오류] 다운로드 실패 ({filename}): {result.stderr}")
        return None

    # gog가 파일을 저장한 경로 찾기
    if os.path.exists(target_path):
        return target_path

    # 경로가 다를 수 있으므로 gog 출력에서 확인
    for line in result.stdout.split("\n"):
        if "path\t" in line:
            saved_path = line.split("\t", 1)[1].strip()
            if os.path.exists(saved_path):
                return saved_path

    return target_path if os.path.exists(target_path) else None

# ─── OpenAI Vision API ──────────────────────────────────

def extract_coupon_info(image_path, api_key):
    """
    OpenAI Vision API(GPT-4o)로 이미지에서 쿠폰 정보 추출
    반환: {"product_name": ..., "discount_amount": ..., "expiration_date": ..., "notes": ...}
    """
    # 이미지를 base64로 인코딩
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    # MIME 타입 추정
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp",
                ".gif": "image/gif"}
    mime = mime_map.get(ext, "image/jpeg")

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "이 이미지에 있는 쿠폰 정보를 추출해주세요.\n"
                            "반드시 아래 JSON 형식으로만 답변하세요. 다른 설명은 하지 마세요.\n"
                            "```json\n"
                            "{\n"
                            '  "product_name": "제품명 (없으면 빈칸)",\n'
                            '  "discount_amount": "할인내용 (예: 50% 할인, 3000원 할인, 1+1 등. 없으면 빈칸)",\n'
                            '  "expiration_date": "YYYY-MM-DD (유효기간. 없으면 빈칸)",\n'
                            '  "notes": "기타 참고사항 (브랜드명, 조건 등)"\n'
                            "}\n"
                            "```\n"
                            "JSON 코드 블록만 출력하고, 추출할 수 없는 필드는 빈 문자열로 두세요."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{img_b64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 500,
        "temperature": 0.1
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            tokens = result["usage"]["total_tokens"]
            print(f"  (토큰: {tokens}개)")

            # JSON 추출 (```json ... ``` 또는 순수 JSON)
            json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1).strip()
            
            # 순수 JSON 객체 파싱 시도
            parsed = json.loads(content)
            # 필드 기본값
            return {
                "product_name": parsed.get("product_name", "") or "",
                "discount_amount": parsed.get("discount_amount", "") or "",
                "expiration_date": parsed.get("expiration_date", "") or "",
                "notes": parsed.get("notes", "") or "",
                "raw_response": content
            }
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 원본 텍스트에서 정보 추출 시도
        print(f"  [경고] JSON 파싱 실패, 원본 텍스트 저장")
        return {
            "product_name": "",
            "discount_amount": "",
            "expiration_date": "",
            "notes": content[:200],
            "raw_response": content
        }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")[:200]
        print(f"  [오류] OpenAI API 오류 ({e.code}): {err_body}")
        return None
    except Exception as e:
        print(f"  [오류] Vision API 호출 실패: {e}")
        return None

# ─── Supabase ───────────────────────────────────────────

def supabase_request(method, path, data=None, anon_key="", svc_key=""):
    """Supabase REST API 호출 (service_role 키 우선)"""
    url = f"{os.environ.get('SUPABASE_URL', '')}{path}"
    headers = {
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    if svc_key:
        headers["apikey"] = svc_key
        headers["Authorization"] = f"Bearer {svc_key}"
    else:
        headers["apikey"] = anon_key
        headers["Authorization"] = f"Bearer {anon_key}"

    data_bytes = json.dumps(data).encode("utf-8") if data else None
    
    req = urllib.request.Request(url, data=data_bytes, headers=headers,
                                  method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")[:200]
        print(f"  [오류] Supabase {method} {path}: {e.code} {err}")
        return None

def _pick_storage_key(svc_key, anon_key):
    """service_role 키 우선, 없으면 anon 키 사용. 둘 다 없으면 None."""
    if svc_key and len(svc_key) >= 20:
        return svc_key
    if anon_key and len(anon_key) >= 20:
        return anon_key
    return None


def upload_to_storage(file_path, filename, svc_key="", anon_key=""):
    """Supabase Storage에 이미지 업로드, public URL 반환

    키 우선순위: service_role → anon (anon은 storage INSERT 정책이 있으면 가능)
    """
    api_key = _pick_storage_key(svc_key, anon_key)
    if not api_key:
        print("  [오류] 업로드용 Supabase 키가 없습니다 (svc/anon 모두 없음)")
        return None

    upload_name = f"coupons/{int(time.time())}_{filename}"
    storage_url = (
        f"{os.environ.get('SUPABASE_URL', '')}"
        f"/storage/v1/object/coupon_images/{upload_name}"
    )

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "image/jpeg"
    }

    req = urllib.request.Request(
        storage_url, data=file_bytes, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"  이미지 업로드 성공")
            return (f"{os.environ.get('SUPABASE_URL', '')}"
                    f"/storage/v1/object/public/coupon_images/{upload_name}")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")[:200]
        print(f"  [오류] Storage 업로드 실패: {e.code} {err}")
        return None


def insert_coupon(coupon_data, svc_key="", anon_key=""):
    """Supabase coupons 테이블에 레코드 삽입 (anon 키 fallback 지원)"""
    return supabase_request(
        "POST", "/rest/v1/coupons",
        data=coupon_data,
        anon_key=anon_key,
        svc_key=svc_key
    )

# ─── 처리 상태 관리 ─────────────────────────────────────

def load_state():
    """이미 처리한 파일 ID 목록 로드"""
    state_file = STATE_FILE
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"processed": []}

def save_state(state):
    """처리 완료 상태 저장"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ─── 메인 ───────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 50)
    print("  쿠폰 OCR 자동 처리 파이프라인")
    print(f"  {'[DRY RUN] 실제 저장 안함' if dry_run else '[실행]'}")
    print("=" * 50)

    # 1. API 키 로드
    print("\n[1/5] API 키 확인...")
    
    # 프로젝트/공용 credential 파일 로드
    load_env_file(os.path.expanduser("~/Documents/github/coupon-manager/upload-coupon.sh"))
    load_env_file(os.path.expanduser("~/Documents/github/coupon-manager/process-coupons.sh"))
    load_env_file(os.path.expanduser("~/repos/lecturenote/.env"))
    
    openai_key = get_openai_key()
    supabase_url, anon_key, svc_key = get_supabase_keys()

    if not anon_key and not svc_key:
        # index.html에서 anon 키 추출 시도
        try:
            import re as _re
            html = (open(os.path.expanduser("~/Documents/github/coupon-manager/index.html")).read())
            m = _re.search(r"SUPABASE_ANON_KEY\s*=\s*'([^']+)'", html)
            if m and len(m.group(1)) >= 20:
                os.environ["SUPABASE_ANON"] = m.group(1)
                supabase_url, anon_key, svc_key = get_supabase_keys()
        except Exception:
            pass

    if not openai_key or len(openai_key) < 20:
        print("  [오류] OpenAI API 키를 찾을 수 없습니다 (~/repos/lecturenote/.env)")
        sys.exit(1)
    print(f"  ✅ OpenAI API 키 확인됨 ({len(openai_key)}자)")

    if not supabase_url:
        print("  [오류] SUPABASE_URL 환경변수가 없습니다")
        sys.exit(1)
    print(f"  ✅ Supabase 연결 확인됨")

    # 2. Drive 파일 목록 조회
    print("\n[2/5] Google Drive 폴더 확인...")
    files = drive_list_files(DRIVE_FOLDER_ID)
    if not files:
        print("  폴더에 파일이 없습니다.")
        return

    # 이미지 파일만 필터링
    image_files = [f for f in files
                   if f.get("mimeType", "").startswith("image/")]
    print(f"  총 {len(files)}개 파일 중 이미지: {len(image_files)}개")

    if not image_files:
        print("  처리할 이미지가 없습니다.")
        return

    # 3. 새 파일(아직 처리 안 한) 확인
    print("\n[3/5] 새 이미지 선별...")
    state = load_state()
    processed_ids = set(state.get("processed", []))
    new_files = [f for f in image_files if f.get("id") not in processed_ids]
    print(f"  신규: {len(new_files)}개 (이미 처리: {len(image_files) - len(new_files)}개)")
    print(f"  누적 처리 완료: {len(processed_ids)}개")

    if not new_files:
        print("\n✅ 새로 처리할 이미지가 없습니다.")
        return

    if not (svc_key and len(svc_key) >= 20) and not (anon_key and len(anon_key) >= 20):
        print("\n[오류] Supabase 저장용 키가 없습니다")
        print("  service_role 키 또는 anon 키가 필요합니다.")
        print("  확인 위치: ~/Documents/github/coupon-manager/upload-coupon.sh")
        print("              ~/Documents/github/coupon-manager/index.html (anon)")
        sys.exit(1)

    # 4. 각 이미지 처리
    for idx, file_info in enumerate(new_files, 1):
        file_id = file_info["id"]
        filename = file_info["name"]
        print(f"\n{'─' * 40}")
        print(f"[{idx}/{len(new_files)}] {filename}")
        print(f"  ID: {file_id}")
        print(f"  크기: {int(file_info.get('size', 0)) / 1024:.1f} KB")

        # 4. 다운로드
        print("\n[4/5] 이미지 다운로드...")
        local_path = drive_download(file_id, filename)
        if not local_path or not os.path.exists(local_path):
            print(f"  [오류] 다운로드 실패, 다음 파일로 넘어갑니다")
            continue
        print(f"  저장: {local_path}")

        # 5. OpenAI Vision API로 쿠폰 정보 추출
        print("\n[5/5] OCR 분석 (GPT-4o Vision)...")
        info = extract_coupon_info(local_path, openai_key)
        if info is None:
            print(f"  [오류] OCR 분석 실패")
            continue

        print(f"  제품명: {info['product_name'] or '?'}")
        print(f"  할인:   {info['discount_amount'] or '?'}")
        print(f"  기한:   {info['expiration_date'] or '?'}")
        print(f"  비고:   {info.get('notes', '') or '?'}")

        # Dry run이면 저장 안 함
        if dry_run:
            print(f"  [DRY RUN] 저장 안함")
            state["processed"].append(file_id)
            save_state(state)
            continue

        # 6. Supabase Storage에 이미지 업로드
        image_url = upload_to_storage(local_path, filename, svc_key=svc_key, anon_key=anon_key)
        if not image_url:
            print(f"  [경고] 이미지 업로드 실패, DB에는 경로 없이 저장")
            image_url = ""

        # 7. Supabase DB에 저장
        expiration = info.get("expiration_date", "")
        # 날짜 형식 검증
        if expiration and not re.match(r"^\d{4}-\d{2}-\d{2}$", expiration):
            expiration = ""

        coupon_record = {
            "product_name": info.get("product_name", "").strip() or filename.replace(".jpg","").replace(".png",""),
            "discount_amount": info.get("discount_amount", "").strip(),
            "expiration_date": expiration if expiration else None,
            "image_url": image_url,
            "status": "active",
            "notes": info.get("notes", "").strip()
        }

        result = insert_coupon(coupon_record, svc_key=svc_key, anon_key=anon_key)
        if result:
            print(f"  ✅ 쿠폰 저장 완료! (ID: {result[0]['id'] if isinstance(result, list) else 'ok'})")
        else:
            print(f"  [경고] DB 저장 실패")

        # 처리 완료 기록
        state["processed"].append(file_id)
        save_state(state)
        print(f"  📝 처리 상태 저장 완료")

        # API 호출 간격 (rate limit)
        time.sleep(1)

    # 요약
    print(f"\n{'=' * 50}")
    print(f"  처리 완료!")
    print(f"  처리된 새 이미지: {len(new_files)}개")
    print(f"  누적 처리: {len(state['processed'])}개")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
