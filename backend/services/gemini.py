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
    # 💡 프론트엔드 에러 방지를 위해 가짜 응답도 동일한 마크다운 형식으로 맞춰줍니다.
    if not api_key:
        return (
            f"### 🛡️AI 분석 리포트\n"
            f"- **분류 결과:** 판단 보류 (Unknown)\n"
            f"- **사이트 정체:** 백엔드 API 키 누락 (UI 테스트 모드)\n"
            f"- **판단 근거:** 현재 백엔드에 Gemini API 키가 연결되지 않아 더미 텍스트가 출력됩니다.\n"
            f"- **행동 지침:** 백엔드 개발자에게 `.env` 파일 설정을 요청하세요."
        )

    genai.configure(api_key=api_key)
    
    # 2. 🌟 최신 2.0 Flash 모델 적용 (가장 빠르고 똑똑한 최신 추론 모델)
    model = genai.GenerativeModel('gemini-3.1-flash-lite')
    
    # 3. 🌟 8종 카테고리 정밀 분석 프롬프트 구성
    text_prompt = f"""
        당신은 보안 앱 'PhishGuard'의 AI 분석관입니다. 아래 [카테고리 리스트] 중 URL과 페이지 내용을 분석하여 가장 적합한 하나를 반드시 선택하십시오.

        [카테고리 리스트 - 답변 시 이 중 하나를 정확히 사용하세요]
        - Safe: 안전한 사이트
        - Phishing: 일반 피싱/계정 탈취
        - Impersonation: 기관 사칭
        - Financial: 금융/대출 사기
        - Malware: 악성코드
        - Gambling: 불법 도박
        - Adult: 유해 콘텐츠/성인물
        - Unknown: 접속 불가/분석 불가

        [제약 사항]
        1. **분류 결과** : 위 [카테고리 리스트]에 명시된 한글 키워드(예: 기관 사칭, 금융 사기 등)를 그대로 사용하십시오.
        2. 사이트 : 군더더기 없이 간결하게 요약하십시오.
        3. 판단 근거 : URL의 패턴과 화면의 시각적 요소를 근거로 들어주십시오. (1~2문장)
        4. 행동 지침 : 사용자에게 정중한 존댓말로 경고나 안내를 하십시오 (1문장).

        [출력 양식 - 이 형식을 반드시 지키십시오]
        ### 🛡️ AI 분석 리포트
        - 분류 결과: [카테고리 키워드 한글 버전 작성, 예: 기관 사칭]
        - 사이트 정체: [단문의 한 줄 요약]
        - 판단 근거: [구체적인 단서 요약, 1-2문장]
        - 행동 지침: [정중한 존댓말 지침, 1문장]

        ---
        *본 리포트는 AI 분석 결과에 기반한 참고 자료이며, 최종 선택과 책임은 사용자에게 있습니다.*

        [분석 대상 데이터]
        - 대상 URL: {url}
        - 1차 위험도 점수: {risk_score} / 100점
        - 추출 텍스트: {site_text[:1000]}
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
        # 비동기로 API 호출 (텍스트와 이미지가 묶인 prompt_parts 배열을 넘김)
        response = await model.generate_content_async(prompt_parts)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Gemini API 호출 에러: {e}")
        # 💡 에러가 났을 때도 프론트엔드 화면이 깨지지 않도록 동일한 양식으로 에러 리포트 반환
        return (
            f"### 🛡️ PhishGuard AI 분석 리포트\n"
            f"- **분류 결과:** 판단 보류 (Unknown)\n"
            f"- **사이트 정체:** 분석 시스템 오류 발생\n"
            f"- **판단 근거:** AI 모델 호출 중 서버 오류가 발생했습니다. ({str(e)})\n"
            f"- **행동 지침:** 잠시 후 다시 시도해 주세요."
        )