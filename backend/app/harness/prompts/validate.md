{% include "_context.md" %}
## 지켜야 할 규칙
{% for rule in policy.rules -%}
- {{ rule }}
{% else -%}
- (없음)
{% endfor %}
## 검토할 결과
{{ result_text }}

## 할 일
결과가 입력과 모순되는지, 확인되지 않은 숫자를 사실처럼 썼는지, 과장·단정 표현이 있는지, 가정 표시가 빠졌는지 검토해 issues로 적어라.
