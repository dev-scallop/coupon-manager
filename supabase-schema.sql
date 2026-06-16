-- ═══════════════════════════════════════════════════════════════
-- 쿠폰 관리 앱 - Supabase 스키마
-- 
-- Supabase Dashboard > SQL Editor 에서 아래 SQL을 실행하세요
-- ═══════════════════════════════════════════════════════════════

-- 1. coupons 테이블 생성
CREATE TABLE IF NOT EXISTS public.coupons (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  product_name text NOT NULL,
  discount_amount text,
  expiration_date date,
  image_url text,
  status text DEFAULT 'active' CHECK (status IN ('active','used','expired')),
  notes text,
  created_at timestamptz DEFAULT now(),
  used_at timestamptz
);

-- 2. RLS 활성화 (선택 - 필요하면)
ALTER TABLE public.coupons ENABLE ROW LEVEL SECURITY;

-- 3. 누구나 읽기/쓰기 가능 (개인용 앱이므로)
CREATE POLICY "Allow all on coupons" ON public.coupons
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 4. Storage 버킷 생성
INSERT INTO storage.buckets (id, name, public)
VALUES ('coupon_images', 'coupon_images', true)
ON CONFLICT (id) DO NOTHING;

-- 5. Storage 접근 정책
CREATE POLICY "Allow public read coupon_images" ON storage.objects
  FOR SELECT
  USING (bucket_id = 'coupon_images');

CREATE POLICY "Allow public insert coupon_images" ON storage.objects
  FOR INSERT
  WITH CHECK (bucket_id = 'coupon_images');
