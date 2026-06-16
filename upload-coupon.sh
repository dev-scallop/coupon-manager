#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Supabase 쿠폰 데이터 업로드 (Hermes 전용)
#
# 사용법:
#   ./upload-coupon.sh "제품명" "할인금액" "만료일(YYYY-MM-DD)" "이미지URL" "비고"
#
# 예시:
#   ./upload-coupon.sh "스타벅스 아메리카노" "1+1" "2026-06-20" "" "프로모션"
# ═══════════════════════════════════════════════════════════════

SUPABASE_URL="https://yyjmrnuyadwzzkuzntjd.supabase.co"
SERVICE_KEY="eyJhbG...ieFw"

PRODUCT_NAME="$1"
DISCOUNT="$2"
EXPIRATION="$3"
IMAGE_URL="$4"
NOTES="$5"

if [ -z "$PRODUCT_NAME" ]; then
  echo "사용법: $0 <제품명> [할인금액] [만료일] [이미지URL] [비고]"
  exit 1
fi

JSON=$(cat <<EOF
{
  "product_name": "$PRODUCT_NAME",
  "discount_amount": "$DISCOUNT",
  "expiration_date": "$EXPIRATION",
  "image_url": "$IMAGE_URL",
  "status": "active",
  "notes": "$NOTES"
}
EOF
)

echo "=== Supabase에 쿠폰 등록 ==="
echo "제품명: $PRODUCT_NAME"
echo "할인: $DISCOUNT"
echo "만료: $EXPIRATION"

RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/rest/v1/coupons" \
  -H "apikey: ${SERVICE_KEY}" \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d "$JSON")

echo "결과: $RESPONSE" | head -3
echo "=== 완료 ==="
