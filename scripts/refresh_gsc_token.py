"""
Google Search Console / Indexing API 토큰 재발급
실행: python scripts/refresh_gsc_token.py
브라우저가 열리면 구글 계정으로 로그인 후 승인하면 됩니다.
"""
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

CREDS_PATH = Path(__file__).parent.parent / "config" / "credentials.json"
TOKEN_PATH  = Path(__file__).parent.parent / "config" / "gsc_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/indexing",
]

def main():
    print("Google 인증 재발급을 시작합니다...")
    print("브라우저가 열리면 kgbae99@gmail.com 계정으로 로그인 후 승인하세요.\n")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    token_data = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes) if creds.scopes else SCOPES,
        "expiry":        creds.expiry.isoformat() if creds.expiry else "",
    }
    TOKEN_PATH.write_text(json.dumps(token_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n토큰 저장 완료: {TOKEN_PATH}")
    print("이제 request_indexing.py 를 실행하세요.")

if __name__ == "__main__":
    main()
