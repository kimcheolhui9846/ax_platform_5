{% block system %}
{% include "_task.md" %}

## 할 일
사용자 메시지의 섹션 내용을 보여 주는 참고 이미지 한 장을 그려라.
글자·로고·실존 인물·실제 상표는 넣지 않는다. 시안을 떠올리게 하는 참고용이며 실제 상품 사진처럼 꾸미지 않는다.
{% endblock %}
{% block user %}
{% include "_context.md" %}

## 그림으로 보여 줄 섹션
{{ heading | inline }}
{{ text | block }}
{% endblock %}
