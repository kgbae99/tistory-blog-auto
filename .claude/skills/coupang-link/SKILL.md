---
name: coupang-link
description: 쿠팡 파트너스 수익 링크를 생성하고 블로그 포스트에 삽입할 때 활성화. API 호출, HMAC 인증, 상품 선정, HTML 위젯 코드 생성 가이드.
---

# 쿠팡 파트너스 링크 생성 스킬

## API 사용법

### HMAC 인증 생성
```python
import hmac
import hashlib
import time

def generate_hmac(method, url, secret_key, access_key):
    datetime = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    message = datetime + method + url
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime}, signature={signature}"
```

### 상품 검색 호출
- URL: `https://api-gateway.coupang.com/v2/providers/affiliate_open_api/apis/openapi/products/search`
- Method: GET
- Parameters: `keyword`, `limit` (최대 100), `subId`

### 딥링크 생성
- URL: `https://api-gateway.coupang.com/v2/providers/affiliate_open_api/apis/openapi/deeplink`
- Method: POST
- Body: `{"coupangUrls": ["https://www.coupang.com/vp/products/xxxxx"]}`

## 상품 선정 기준
1. 리뷰수 100개 이상
2. 평점 4.0 이상
3. 로켓배송 상품 우선
4. 가격대 다양화 (저/중/고)
5. 포스트 키워드와 연관성 높은 상품

## 블로그 삽입 HTML
```html
<div class="coupang-recommend" style="margin: 20px 0; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px;">
  <p style="font-size: 14px; color: #666; margin-bottom: 10px;">건강온도사 추천 제품</p>
  <a href="{affiliate_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: #333;">
    <div style="display: flex; align-items: center; gap: 15px;">
      <img src="{image_url}" alt="{product_name}" style="width: 120px; height: 120px; object-fit: contain;">
      <div>
        <h4 style="margin: 0 0 8px 0; font-size: 16px;">{product_name}</h4>
        <p style="margin: 0 0 5px 0; font-size: 18px; font-weight: bold; color: #e44d26;">{price}원</p>
        <p style="margin: 0; font-size: 13px; color: #f5a623;">★ {rating} ({review_count}개 리뷰)</p>
        <span style="display: inline-block; margin-top: 8px; padding: 6px 16px; background: #e44d26; color: white; border-radius: 4px; font-size: 14px;">쿠팡에서 보기</span>
      </div>
    </div>
  </a>
</div>
```

## 필수 고지문
포스트 하단에 반드시 포함:
```html
<p style="font-size: 12px; color: #999; margin-top: 30px;">
이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
</p>
```
