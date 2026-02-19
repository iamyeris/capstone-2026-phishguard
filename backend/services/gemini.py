import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일에서 환경변수 불러오기
load_dotenv()

async def generate_security_report(url: str, risk_score: int, site_text: str) -> str:
    """
    Gemini API를 호출하여 사용자에게 보여줄 최종 보안 리포트를 생성합니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return (
            f"⚠️ [UI 테스트용 더미 리포트]\n"
            f"요청하신 URL({url})의 위험도는 {risk_score}점입니다.\n"
            f"현재 백엔드에 Gemini API 키가 연결되지 않아 기본 텍스트가 출력됩니다."
        )

    genai.configure(api_key=api_key)
    
    # 모델 설정 (가장 빠르고 가성비 좋은 모델 추천)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    당신은 사이버 보안 전문가 'PhishGuard'입니다.
    다음 웹사이트 정보를 바탕으로 사용자에게 위험성을 경고하거나 안심시키는 2~3줄의 짧고 명확한 한국어 리포트를 작성해주세요.

    - 대상 URL: {url}
    - 1차 분석 위험도 점수: {risk_score} / 100 (점수가 높을수록 위험)
    - 사이트에서 추출된 텍스트 일부: {site_text[:500]}
    
    주의사항:
    - 전문 용어는 줄이고, 일반 사용자가 즉각적으로 행동(접속 중단 등)을 판단할 수 있게 작성할 것.
    - 마크다운이나 특수문자 없이 앱에 바로 띄울 수 있는 깔끔한 평문으로 반환할 것.
    """
    
    try:
        # 비동기로 API 호출
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API 호출 에러: {e}")
        return "AI 분석 리포트를 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."