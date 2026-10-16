"""상품기획 하네스. 바꾸고 싶은 단계만 BaseHarness 메서드를 오버라이드한다."""
from app.harness.base import BaseHarness

from .output_schema import ProductPlanningContent
from .validators import VALIDATORS


class Harness(BaseHarness):
    content_model = ProductPlanningContent
    validators = VALIDATORS
