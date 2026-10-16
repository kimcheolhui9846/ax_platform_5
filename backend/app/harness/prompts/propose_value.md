{% block system %}
{% include "_task.md" %}

## 할 일
사용자가 한 항목에 여러 번 "모르겠어요"라고 답했다. 지금까지의 맥락으로 그 항목의 가장 그럴듯한 후보 값을
요청된 개수만큼 제안하라. 이미 제시했지만 고르지 않은 후보는 다시 내지 마라.
text에는 "이 중 가장 가까운 걸 고르거나 고쳐 주세요"처럼 고르기 쉬운 안내 문장을 써라.
{% endblock %}
{% block user %}
{% include "_context.md" %}

## 이번 요청
- 항목: {{ field.name }} ({{ field.label }})
- 이미 제시한 후보:
{% for c in previous %}
  - {{ c }}
{% else %}
  - (없음)
{% endfor %}
- 후보 개수: {{ profile.alternative_count }}개
- 현재 쉬운 질문 단계: {{ level }}
{% endblock %}
