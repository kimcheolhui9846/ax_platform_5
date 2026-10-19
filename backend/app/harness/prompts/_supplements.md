## 보완 정보 (사용자 입력 · 검증 전)
{% for name, item in state.supplements.items() %}
- {{ name }} ({{ policy.supplement_labels.get(name, name) }}): {{ item.value | inline }}
{% else %}
- (없음)
{% endfor %}
