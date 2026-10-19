{% block system %}
{% include "_task.md" %}

## 지켜야 할 규칙
{% for rule in policy.rules %}
- {{ rule }}
{% else %}
- (없음)
{% endfor %}

## 할 일
사용자 메시지의 결과가 입력과 모순되는지, 확인되지 않은 숫자를 사실처럼 썼는지, 과장·단정 표현이 있는지,
가정 표시가 빠졌는지 검토해 issues로 적어라.
{% endblock %}
{% block user %}
{% include "_context.md" %}

{% include "_supplements.md" %}

## 검토할 결과
{{ result_text | block }}
{% endblock %}
