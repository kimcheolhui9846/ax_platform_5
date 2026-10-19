{% extends "generate.md" %}
{% block user %}
{{ super() }}
## 이번에 쓸 범위
- 결과 항목 중 {{ part.content | join(", ") }}만 쓴다. 다른 항목은 다른 호출이 쓴다.
- 카드도 이 항목을 다루는 것만 쓴다.
{% endblock %}
