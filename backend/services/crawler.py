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

        try:
            # 중요: 피싱 사이트 대기 시간을 최대 15초로 제한 (서버 마비 방지)
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")

            # 1. 텍스트 추출 (나중에 BERT 모델이 분석할 재료)
            result["text"] = await page.inner_text("body")

            # 2. 스크린샷 캡처 (AI 비전 모델이나 앱 UI에서 보여줄 용도)
            # 이미지를 파일로 저장하지 않고 Base64 문자열로 변환해서 바로 넘김
            screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
            result["screenshot_base64"] = base64.b64encode(screenshot_bytes).decode("utf-8")

        except PlaywrightTimeoutError:
            result["error"] = "접속 시간 초과: 사이트가 응답하지 않거나 접속이 차단되었습니다."
        except Exception as e:
            result["error"] = f"접속 실패: {str(e)}"
        finally:
            await browser.close()

    return result