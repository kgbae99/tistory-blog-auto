"""추가 이미지 다운로드 스크립트 - assets/images/ 풀 확장."""
import time
import urllib.request
from pathlib import Path

ASSETS = Path(__file__).parent.parent / "assets" / "images"
ASSETS.mkdir(parents=True, exist_ok=True)

# 다운로드할 이미지 목록 (Unsplash 검증된 photo ID)
DOWNLOAD_LIST = [
    # 건강 추가 (health_16 ~ health_30)
    ("health_16.jpg", "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=600&q=80"),
    ("health_17.jpg", "https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?w=600&q=80"),
    ("health_18.jpg", "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=600&q=80"),
    ("health_19.jpg", "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=600&q=80"),
    ("health_20.jpg", "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=600&q=80"),
    ("health_21.jpg", "https://images.unsplash.com/photo-1588776814546-1ffbb7d36308?w=600&q=80"),
    ("health_22.jpg", "https://images.unsplash.com/photo-1511688878353-3a2f5be94cd7?w=600&q=80"),
    ("health_23.jpg", "https://images.unsplash.com/photo-1530497610245-94d3c16cda28?w=600&q=80"),
    ("health_24.jpg", "https://images.unsplash.com/photo-1544991875-5dc1b05f1571?w=600&q=80"),
    ("health_25.jpg", "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=600&q=80"),
    # 음식 추가 (food_16 ~ food_30)
    ("food_16.jpg", "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600&q=80"),
    ("food_17.jpg", "https://images.unsplash.com/photo-1467453678174-768ec283a940?w=600&q=80"),
    ("food_18.jpg", "https://images.unsplash.com/photo-1488459716781-31db52582fe9?w=600&q=80"),
    ("food_19.jpg", "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=600&q=80"),
    ("food_20.jpg", "https://images.unsplash.com/photo-1490818387583-1baba5e638af?w=600&q=80"),
    ("food_21.jpg", "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=600&q=80"),
    ("food_22.jpg", "https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=600&q=80"),
    ("food_23.jpg", "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&q=80"),
    ("food_24.jpg", "https://images.unsplash.com/photo-1547592180-85f173990554?w=600&q=80"),
    ("food_25.jpg", "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=600&q=80"),
    # 운동 추가 (exercise_10 ~ exercise_20)
    ("exercise_10.jpg", "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&q=80"),
    ("exercise_11.jpg", "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=600&q=80"),
    ("exercise_12.jpg", "https://images.unsplash.com/photo-1526506118085-60ce8714f8c5?w=600&q=80"),
    ("exercise_13.jpg", "https://images.unsplash.com/photo-1574680178050-55c6a6a96e0a?w=600&q=80"),
    ("exercise_14.jpg", "https://images.unsplash.com/photo-1529516548873-9ce57c8f155e?w=600&q=80"),
    ("exercise_15.jpg", "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=600&q=80"),
    # 피부/뷰티 추가 (skin_06 ~ skin_15)
    ("skin_06.jpg", "https://images.unsplash.com/photo-1601925228008-8c1bcdcf2b6e?w=600&q=80"),
    ("skin_07.jpg", "https://images.unsplash.com/photo-1570194065650-d99fb4bedf0a?w=600&q=80"),
    ("skin_08.jpg", "https://images.unsplash.com/photo-1522338242992-e1a54906a8da?w=600&q=80"),
    ("skin_09.jpg", "https://images.unsplash.com/photo-1523263685509-57c1d050d19b?w=600&q=80"),
    ("skin_10.jpg", "https://images.unsplash.com/photo-1552693673-1bf958298935?w=600&q=80"),
    ("skin_11.jpg", "https://images.unsplash.com/photo-1519415510236-718bdfcd89c8?w=600&q=80"),
    # 수면/휴식 추가 (sleep_04 ~ sleep_10)
    ("sleep_04.jpg", "https://images.unsplash.com/photo-1541199249251-f713e6145474?w=600&q=80"),
    ("sleep_05.jpg", "https://images.unsplash.com/photo-1520206183501-b80df61043c2?w=600&q=80"),
    ("sleep_06.jpg", "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=600&q=80"),
    # 다이어트 추가 (diet_05 ~ diet_10)
    ("diet_05.jpg", "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&q=80"),
    ("diet_06.jpg", "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=600&q=80"),
    ("diet_07.jpg", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80"),
    # IT/테크 이미지 (tech_01 ~ tech_30)
    ("tech_01.jpg", "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&q=80"),
    ("tech_02.jpg", "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&q=80"),
    ("tech_03.jpg", "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=600&q=80"),
    ("tech_04.jpg", "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=600&q=80"),
    ("tech_05.jpg", "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=600&q=80"),
    ("tech_06.jpg", "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80"),
    ("tech_07.jpg", "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&q=80"),
    ("tech_08.jpg", "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=600&q=80"),
    ("tech_09.jpg", "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=600&q=80"),
    ("tech_10.jpg", "https://images.unsplash.com/photo-1484417894907-623942c8ee29?w=600&q=80"),
    ("tech_11.jpg", "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=600&q=80"),
    ("tech_12.jpg", "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=600&q=80"),
    ("tech_13.jpg", "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=600&q=80"),
    ("tech_14.jpg", "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&q=80"),
    ("tech_15.jpg", "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&q=80"),
    ("tech_16.jpg", "https://images.unsplash.com/photo-1484788984921-03950022c38b?w=600&q=80"),
    ("tech_17.jpg", "https://images.unsplash.com/photo-1547394765-185e1e68f34e?w=600&q=80"),
    ("tech_18.jpg", "https://images.unsplash.com/photo-1587614382346-4ec70e388b28?w=600&q=80"),
    ("tech_19.jpg", "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=600&q=80"),
    ("tech_20.jpg", "https://images.unsplash.com/photo-1604754742629-3e5728249d73?w=600&q=80"),
    ("tech_21.jpg", "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=600&q=80"),
    ("tech_22.jpg", "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=600&q=80"),
    ("tech_23.jpg", "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=600&q=80"),
    ("tech_24.jpg", "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?w=600&q=80"),
    ("tech_25.jpg", "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=600&q=80"),
    ("tech_26.jpg", "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600&q=80"),
    ("tech_27.jpg", "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=600&q=80"),
    ("tech_28.jpg", "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=600&q=80"),
    ("tech_29.jpg", "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=600&q=80"),
    ("tech_30.jpg", "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&q=80"),
]

headers = {"User-Agent": "Mozilla/5.0"}
ok, fail = 0, 0

for fname, url in DOWNLOAD_LIST:
    dest = ASSETS / fname
    if dest.exists():
        print(f"  SKIP {fname}")
        continue
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            dest.write_bytes(r.read())
        print(f"  OK   {fname}")
        ok += 1
        time.sleep(0.3)
    except Exception as e:
        print(f"  FAIL {fname}: {e}")
        fail += 1

print(f"\n완료: {ok}개 다운로드, {fail}개 실패")
print(f"총 이미지: {len(list(ASSETS.glob('*.jpg')))}개")
