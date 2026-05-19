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
            f"### 🛡️ PhishGuard AI 분석 리포트\n"
            f"- **분류 결과:** ⑧ 판단 보류 (Unknown)\n"
            f"- **사이트 정체:** 백엔드 API 키 누락 (UI 테스트 모드)\n"
            f"- **판단 근거:** 현재 백엔드에 Gemini API 키가 연결되지 않아 더미 텍스트가 출력됩니다.\n"
            f"- **행동 지침:** 백엔드 개발자에게 `.env` 파일 설정을 요청하세요."
        )

    genai.configure(api_key=api_key)
    
    # 2. 🌟 최신 2.0 Flash 모델 적용 (가장 빠르고 똑똑한 최신 추론 모델)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # 3. 🌟 8종 카테고리 정밀 분석 프롬프트 구성
    text_prompt = f"""
    당신은 보안 앱 'PhishGuard'의 모바일 화면용 리포트를 작성하는 AI 분석관입니다.
    제공된 정보를 바탕으로 사용자가 한눈에 위험을 파악할 수 있도록 **미사여구를 배제하고, 두괄식의 간결한 문장(각 항목별 1~2문장 이내)**으로 작성하세요.

    [분석 대상 정보]
    - 대상 URL: {url}
    - 1차 위험도 점수: {risk_score} / 100점
    - 추출 텍스트: {site_text[:500]}

    [제약 및 수행 사항]
    1. 카테고리 분류: 아래 8개 중 정확히 '하나'만 골라 출력할 것.
    (정상, 일반 피싱, 기관 사칭, 금융 사기, 악성코드, 불법 도박, 유해 콘텐츠, 판단 보류)
    2. 사이트 정체: 군더더기 없이 어떤 사이트인지 명사형으로 명확히 요약할 것.
    3. 판단 근거: 단순히 '징후가 없다'는 말 대신, URL 도메인의 정합성이나 스크린샷 UI 레이아웃 등 구체적인 시각적 단서를 1~2문장으로 요약할 것. (1차 위험도 점수에 대한 언급이나 오탐지 해명은 절대 포함하지 말 것)
    4. 행동 지침: 사용자가 취해야 할 안전 수칙을 친절하고 정중한 존댓말(~하세요, ~하시기 바랍니다)로 1문장 작성할 것.
    5. 면책 조항: 보고서 맨 마지막에 고정된 안내 문구를 반드시 포함할 것.

    [출력 양식 - 마크다운 양식 엄격 준수]
    ### 🛡️ AI 분석 리포트
    - **분류 결과:** [카테고리명]
    - **사이트 정체:** [단문의 한 줄 요약]
    - **판단 근거:** [구체적인 단서 요약, 최대 2문장]
    - **행동 지침:** [정중한 존댓말 지침, 1문장]

    ---
    *본 리포트는 AI 분석 결과에 기반한 참고 자료이며, 최종 사이트 이용 여부에 대한 선택과 책임은 사용자에게 있습니다.*
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
            f"- **분류 결과:** ⑧ 판단 보류 (Unknown)\n"
            f"- **사이트 정체:** 분석 시스템 오류 발생\n"
            f"- **판단 근거:** AI 모델 호출 중 서버 오류가 발생했습니다. ({str(e)})\n"
            f"- **행동 지침:** 잠시 후 다시 시도해 주세요."
        )