{% block system %}
{% include "_task.md" %}

## 할 일
사용자의 처음 입력에서 아래 항목에 해당하는 정보를 찾아라. 입력에 분명히 있는 것만 뽑고 추측으로 채우지 마라.
{% for f in policy.fields %}
- {{ f.name }}: {{ f.label }}
{% endfor %}
뜻이 모호한 표현은 ambiguous에 그대로 적어라.
{% endblock %}
{% block user %}
{% include "_context.md" %}
{% endblock %}
