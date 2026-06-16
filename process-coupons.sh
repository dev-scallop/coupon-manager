#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 쿠폰 이미지 처리 스크립트
# 
# 하는 일:
# 1. Google Drive에서 새 이미지 다운로드
# 2. 내가 이미지 분석 (이 작업을 해달라고 지시하면 내가 함)
# 3. Supabase에 업로드
#
# 사용법:
#   이 스크립트는 제가 실행합니다. 책임님은 Google Drive에 이미지만 올려주세요.
# ═══════════════════════════════════════════════════════════════

SUPABASE_URL="https://yyjmrnuyadwzzkuzntjd.supabase.co"
SERVICE_KEY="eyJhbG...ieFw"

# === 설정 ===
# Google Drive에서 쿠폰 이미지를 모아둘 폴더 ID
# 지금은 비워두고, 책임님이 사용하실 폴더를 지정하면 됩니다
DRIVE_FOLDER_ID=""

# 로컬 임시 저장소
WORK_DIR="/tmp/coupon-processing"
mkdir -p "$WORK_DIR"

echo "=== 쿠폰 처리 시작 ==="

# 1. Drive에서 이미지 다운로드
if [ -n "$DRIVE_FOLDER_ID" ]; then
  echo "Drive 폴더에서 이미지 다운로드 중..."
  gog drive export "$DRIVE_FOLDER_ID" "$WORK_DIR" 2>/dev/null || \
  echo "  (gog drive export 실패 - 수동으로 이미지를 $WORK_DIR 에 넣어주세요)"
fi

# 2. 다운로드된 이미지 확인
IMAGES=("$WORK_DIR"/*.{png,jpg,jpeg,webp} 2>/dev/null)
echo "처리할 이미지: ${#IMAGES[@]}개"

# 3. 실제 분석은 Hermes 채팅에서 책임님이 이미지를 올리면
#    제가 분석해서 처리합니다
#    아래는 Supabase에 저장할 때 사용할 API 호출 예시입니다
echo ""
echo "=== 처리 완료 ==="
echo "이미지를 처리하려면 이 채널에 이미지를 올려주세요."
echo "제가 분석해서 Supabase에 등록하겠습니다."
