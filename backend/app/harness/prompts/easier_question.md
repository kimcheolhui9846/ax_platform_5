{% include "_context.md" %}
## 할 일
사용자가 "{{ field.label }}" 항목에 대해 아래 질문들에 "모르겠어요"라고 답했다.
{% for q in previous -%}
- {{ q }}
{% else -%}
- (없음)
{% endfor %}
이보다 한 단계 더 쉬운 질문 하나를 만들어라. 추상적인 질문 대신 구체적인 예시나 비교 선택으로 바꾸고, 고를 수 있는 선택지를 {{ profile.alternative_count }}~5개 함께 제시하라.
현재 쉬운 질문 단계: {{ level }}
