import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일에서 환경변수 불러오기
load_dotenv()

async def generate_security_report(url: str, risk_score: int, site_text: str, screenshot_base64: str = "") -> str:
    """
    Gemini API를 호출하여 텍스트와 스크린샷(선택)을 종합 분석한 최종 보안 리포트를 생성합니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    # 1. API 키가 없을 때의 안전장치 (문수 님의 UI 테스트용)
    if not api_key:
        return (
            f"⚠️ [UI 테스트용 더미 리포트]\n"
            f"요청하신 URL({url})의 위험도는 {risk_score}점입니다.\n"
            f"현재 백엔드에 Gemini API 키가 연결되지 않아 기본 텍스트가 출력됩니다."
        )

    genai.configure(api_key=api_key)
    
    # 2. 텍스트와 이미지를 모두 처리할 수 있는 가장 빠르고 가성비 좋은 모델
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 3. 텍스트 프롬프트 구성
    text_prompt = f"""
    당신은 사이버 보안 전문가 'PhishGuard'입니다.
    다음 웹사이트 정보를 바탕으로 사용자에게 위험성을 경고하거나 안심시키는 2~3줄의 짧고 명확한 한국어 리포트를 작성해주세요.

    - 대상 URL: {url}
    - 1차 분석 위험도 점수: {risk_score} / 100 (점수가 높을수록 위험)
    - 사이트에서 추출된 텍스트 일부: {site_text[:500]}
    
    요청 사항:
    - 첨부된 웹사이트 스크린샷 이미지가 있다면, 이미지 내의 시각적 요소(사칭된 로고, 수상한 입력 폼 등)도 함께 분석하여 리포트에 반영해주세요.
    - 전문 용어는 줄이고, 일반 사용자가 즉각적으로 행동(접속 중단 등)을 판단할 수 있게 작성하세요.
    - 마크다운이나 특수문자 없이 앱에 바로 띄울 수 있는 깔끔한 평문으로 반환하세요.
    """
    
    # 4. 멀티모달 프롬프트 리스트 구성 (텍스트 + 이미지)
    prompt_parts = [text_prompt]
    
    # 크롤러가 스크린샷을 성공적으로 가져왔다면 프롬프트에 이미지 데이터 추가
    if screenshot_base64:
        prompt_parts.append({
            "mime_type": "image/jpeg", # 크롤러에서 jpeg로 설정했으므로 맞춤
            "data": screenshot_base64
        })
    
    # 5. API 호출 및 결과 반환
    try:
        # 비동기로 API 호출 (단일 텍스트가 아닌 prompt_parts 배열을 통째로 넘김)
        response = await model.generate_content_async(prompt_parts)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API 호출 에러: {e}")
        return "AI 분석 리포트를 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."