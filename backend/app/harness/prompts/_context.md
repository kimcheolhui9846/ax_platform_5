## 사용자가 처음 입력한 내용
{{ state.raw_input }}

## 확인된 사실
{% for name, item in state.facts.items() %}
- {{ name }} ({{ policy.labels.get(name, name) }}): {{ item.value }} (출처: {{ item.source | source_label }})
{% else %}
- (없음)
{% endfor %}

## AI 가정 (사용자 확인 전)
{% for name, item in state.assumptions.items() %}
- {{ name }} ({{ policy.labels.get(name, name) }}): {{ item.value }}
{% else %}
- (없음)
{% endfor %}

## 아직 모르는 항목
{% for name in state.unknowns %}
- {{ name }} ({{ policy.labels.get(name, name) }})
{% else %}
- (없음)
{% endfor %}

## 보완 정보 (사용자 입력 · 검증 전)
{% for name, item in state.supplements.items() %}
- {{ name }} ({{ policy.supplement_labels.get(name, name) }}): {{ item.value }}
{% else %}
- (없음)
{% endfor %}
