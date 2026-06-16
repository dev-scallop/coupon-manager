-- ═══════════════════════════════════════════════════════════════
-- 쿠폰 관리 앱 - Supabase 스키마
-- 
-- Supabase Dashboard > SQL Editor 에서 아래 SQL을 실행하세요
-- ═══════════════════════════════════════════════════════════════

-- ⚠️ 이미 coupons 테이블이 있다면 (1)은 CREATE IF NOT EXISTS라 무시되므로,
--    별도로 다음 한 줄을 먼저 실행해 category 컬럼만 추가하세요:
--    ALTER TABLE public.coupons ADD COLUMN IF NOT EXISTS category text;
--    CREATE INDEX IF NOT EXISTS idx_coupons_category ON public.coupons(category);

-- 1. coupons 테이블 생성
CREATE TABLE IF NOT EXISTS public.coupons (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  product_name text NOT NULL,
  discount_amount text,
  expiration_date date,
  image_url text,
  status text DEFAULT 'active' CHECK (status IN ('active','used','expired')),
  category text,
  notes text,
  created_at timestamptz DEFAULT now(),
  used_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_coupons_category ON public.coupons(category);
CREATE INDEX IF NOT EXISTS idx_coupons_status ON public.coupons(status);
CREATE INDEX IF NOT EXISTS idx_coupons_created_at ON public.coupons(created_at DESC);

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

-- ═══════════════════════════════════════════════════════════════
-- 6. edit_log 테이블 (쿠폰 편집 이력)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.edit_log (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  coupon_id uuid REFERENCES public.coupons(id) ON DELETE CASCADE,
  changes jsonb NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_edit_log_coupon_id ON public.edit_log(coupon_id);
CREATE INDEX IF NOT EXISTS idx_edit_log_created_at ON public.edit_log(created_at DESC);

ALTER TABLE public.edit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all on edit_log" ON public.edit_log
  FOR ALL
  USING (true)
  WITH CHECK (true);
