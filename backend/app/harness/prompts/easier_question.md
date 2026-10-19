{% block system %}
{% include "_task.md" %}

## 할 일
사용자가 한 항목의 질문이 어렵다며 "다른 예시 보기"를 눌렀다. 사용자 메시지의 "이번 요청"에 적힌 항목과 이전 질문을 보고,
그보다 한 단계 더 쉬운 질문 하나를 만들어라. 추상적인 질문 대신 구체적인 예시나 비교 선택으로 바꾸고,
고를 수 있는 선택지를 요청된 개수만큼 함께 제시하라.
{% endblock %}
{% block user %}
{% include "_context.md" %}

## 이번 요청
- 항목: {{ field.name }} ({{ field.label }})
- 어렵다고 한 질문:
{% for q in previous %}
  - {{ q | inline }}
{% else %}
  - (없음)
{% endfor %}
- 선택지 개수: {{ profile.alternative_count }}~5개
- 현재 쉬운 질문 단계: {{ level }}
{% endblock %}
