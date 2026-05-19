import base64
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def fetch_page_info(url: str) -> dict:
    """
    Playwright를 이용해 격리된 환경에서 URL에 접속하고 
    화면 스크린샷과 텍스트 데이터를 수집합니다.
    """
    result = {
        "url": url,
        "text": "",
        "screenshot_base64": "",
        "error": None
    }

    async with async_playwright() as p:
        # headless=True 로 설정하여 화면에 브라우저를 띄우지 않고 백그라운드에서 실행
        browser = await p.chromium.launch(headless=True)
        
        # 봇 차단을 피하기 위해 일반적인 PC 브라우저처럼 User-Agent 위장
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

# 🌟 [추가된 위장술 1] "나는 봇이 아니라 진짜 사람 브라우저야!" 라고 속이는 스크립트 몰래 주입
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            # 🌟 [수정된 대기 방식] 
            # networkidle은 영원히 안 끝날 수 있으니, "load(기본적인 화면 로딩 완료)"까지만 기다림
            await page.goto(url, timeout=15000, wait_until="load")
            
            # 🌟 [추가된 위장술 2] 봇 탐지를 피하기 위해 화면 로딩 후 넉넉하게 3초 대기 (애니메이션, 캡차 통과 등)
            await page.wait_for_timeout(3000)

            # 1. 텍스트 추출
            result["text"] = await page.inner_text("body")

            # 2. 스크린샷 캡처
            screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
            result["screenshot_base64"] = base64.b64encode(screenshot_bytes).decode("utf-8")

        except PlaywrightTimeoutError:
            # 🌟 [수정 3] 만약 네이버처럼 무거운 사이트라서 15초가 넘어가버리면?
            # 에러로 처리해서 앱을 터뜨리는 대신, "지금까지 그려진 화면이라도 찰칵!" 찍고 넘기도록 방어 코드 추가
            print(f"⚠️ 페이지 로딩 타임아웃 (15초 초과). 강제 캡처를 시도합니다: {url}")
            try:
                result["text"] = await page.inner_text("body")
                screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
                result["screenshot_base64"] = base64.b64encode(screenshot_bytes).decode("utf-8")
            except Exception as inner_e:
                result["error"] = f"타임아웃 후 강제 캡처 실패: {str(inner_e)}"
                
        except Exception as e:
            result["error"] = f"접속 실패: {str(e)}"
        finally:
            await browser.close()

    return result