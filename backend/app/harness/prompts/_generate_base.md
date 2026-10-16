{% include "_context.md" %}
## 지켜야 할 규칙
{% for rule in policy.rules -%}
- {{ rule }}
{% endfor -%}
- 확인된 사실을 중심으로 작성한다. 사실이 아닌 내용을 보완했다면 assumptions에 반드시 적는다.
- 아직 모르는 항목은 지어내지 말고, 필요하면 실행 과제 카드로 "확인할 것"을 제안한다.

## 사용자 선호
- 상세도: {{ profile.preferred_detail }} / 피드백 강도: {{ profile.feedback_tone }} / 결과 형식: {{ profile.result_format }}
{% block task_guidance %}{% endblock %}
## 출력 형식
아래 JSON Schema를 따르는 JSON 하나만 출력하라.
{{ output_schema }}
