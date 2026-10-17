{% block system %}
{% include "_task.md" %}

## 지켜야 할 규칙
{% for rule in policy.rules %}
- {{ rule }}
{% endfor %}
- 확인된 사실을 중심으로 작성한다. 사실이 아닌 내용을 보완했다면 assumptions에 반드시 적는다.
- assumptions의 field에는 괄호 앞 내부 이름을 쓴다: {{ policy.fields | map(attribute="name") | join(", ") }}
- 아직 모르는 항목은 지어내지 말고, 필요하면 실행 과제 카드로 "확인할 것"을 제안한다.
{% block task_guidance %}{% endblock %}
{% endblock %}
{% block user %}
{% include "_context.md" %}

## 보완 정보 (사용자 입력 · 검증 전)
{% for name, item in state.supplements.items() %}
- {{ name }} ({{ policy.supplement_labels.get(name, name) }}): {{ item.value }}
{% else %}
- (없음)
{% endfor %}

## 사용자 선호
- 상세도: {{ profile.preferred_detail }} / 피드백 강도: {{ profile.feedback_tone }} / 결과 형식: {{ profile.result_format }}
{% endblock %}
