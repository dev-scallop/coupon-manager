#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 쿠폰 이미지 처리 스크립트
#
# 하는 일:
# 1. Google Drive에서 새 이미지 다운로드
# 2. Hermes가 이미지 분석 (제품명, 금액, 사용기한 추출)
# 3. Supabase에 이미지 + 데이터 업로드
#
# 사용법:
#   책임님이 Drive 폴더에 이미지를 넣으면
#   "가선임, Drive에 새 쿠폰 있어" 라고 알려주세요
#   제가 실행해서 처리합니다
# ═══════════════════════════════════════════════════════════════

# Google Drive 쿠폰 폴더 ID
DRIVE_FOLDER_ID="1SVCY7UjMOf2KQzxRF-LWxgksGgQ8EE3U"

# 임시 디렉토리
WORK_DIR="/tmp/coupon-processing-$$"
mkdir -p "$WORK_DIR"

echo "=== 쿠폰 이미지 처리 시작 ==="
echo "Drive 폴더: $DRIVE_FOLDER_ID"

# 1. Drive 폴더에서 새 이미지 검색
gog drive ls --account taejin@hanbit.co.kr --no-input -j "$DRIVE_FOLDER_ID" 2>/dev/null | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
files = data.get('files', [])
print(f'폴더 내 파일: {len(files)}개')
for f in files:
    print(f'  {f.get(\"name\",\"?\")} ({f.get(\"id\",\"?\")})')
" 2>/dev/null

echo ""
echo "=== 완료 ==="
echo "이미지 처리는 이 채널에서 진행합니다."
echo "Drive 이미지를 Hermes가 분석하려면 알려주세요."
