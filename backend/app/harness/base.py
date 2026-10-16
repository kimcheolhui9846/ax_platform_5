"""모든 과제가 공유하는 하네스 파이프라인.

단계 하나 = 메서드 하나다. 과제 하네스(tasks/<task>/harness.py)는 바꾸고 싶은
단계만 오버라이드한다. 모든 LLM 호출은 _call()을 거쳐 trace에 남는다.
"""
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel

from app.core.results import (
    GenerationResult,
    TaskResult,
    ValidationIssue,
    ValidationReport,
    utcnow,
)
from app.core.state import (
    Answer,
    AnswerType,
    AskedQuestion,
    Assumption,
    CoachingMode,
    HarnessProfile,
    InfoItem,
    InfoSource,
    Question,
    QuestionOption,
    SessionState,
    SessionStatus,
    TraceEntry,
)
from app.harness.errors import GenerationFailed, HarnessError
from app.harness.policy import FieldKind, FieldPolicy, load_policy
from app.harness.prompting import PromptRenderer
from app.harness.stage_models import Diagnosis, GeneratedQuestion, LLMReview, ProposedValues
from app.harness.validation import COMMON_VALIDATORS, Validator, collect_issues
from app.providers.base import LLMProvider, ProviderError, ProviderOutputError

M = TypeVar("M", bound=BaseModel)


def _options(labels: list[str]) -> list[QuestionOption]:
    return [QuestionOption(id=f"o{i}", label=label) for i, label in enumerate(labels, start=1)]


def answer_to_fact(question: Question, answer: Answer) -> tuple[str, InfoSource]:
    """[코드·순수] 값을 담은 답변(선택·직접 입력)을 (값, 출처)로 바꾼다. 잘못된 입력은 HarnessError."""
    match answer.answer_type:
        case AnswerType.OPTION:
            return _option_value(question, answer.option_ids), InfoSource.USER_SELECTED_AI_OPTION
        case AnswerType.FREE_TEXT:
            return _free_text(answer.value), InfoSource.USER_FREE_TEXT
        case _:
            raise HarnessError("선택지나 직접 입력으로만 값을 답할 수 있습니다.")


def _option_value(question: Question, option_ids: list[str]) -> str:
    if not option_ids:
        raise HarnessError("선택한 선택지가 없습니다.")
    if len(option_ids) > 1 and not question.multi_select:
        raise HarnessError("이 질문은 하나만 고를 수 있습니다.")
    labels = {o.id: o.label for o in question.options}
    unknown = [i for i in option_ids if i not in labels]
    if unknown:
        raise HarnessError(f"없는 선택지입니다: {unknown}")
    return ", ".join(labels[i] for i in option_ids)


def _free_text(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        raise HarnessError("직접 입력한 내용이 비어 있습니다.")
    return text


def to_generation_result(parsed: TaskResult) -> GenerationResult:
    """[코드·순수] LLM이 만든 TaskResult를 세션에 저장할 GenerationResult로 바꾼다."""
    return GenerationResult(
        cards=parsed.cards,
        assumptions=parsed.assumptions,
        full_text=parsed.full_text,
        content=parsed.content.model_dump(mode="json"),
    )


GENERIC_GENERATION_ERROR = "결과를 만드는 중 문제가 생겼습니다. 잠시 뒤 다시 시도해 주세요."


def _validation_trace(report: ValidationReport) -> TraceEntry:
    """[코드·순수] 검증 결과 요약 기록. LLM 검토 호출 기록과 kind로 구분한다."""
    return TraceEntry(
        stage="validate",
        output={"kind": "summary", "issues": [i.model_dump() for i in report.issues]},
    )


def _mark_answered(record: AskedQuestion, answer_type: AnswerType, value: str | None) -> None:
    record.answer_type = answer_type
    record.value = value
    record.answered_at = utcnow()


class BaseHarness:
    content_model: ClassVar[type[BaseModel]]
    validators: ClassVar[list[Validator]] = []

    def __init__(self, task_dir: Path, provider: LLMProvider) -> None:
        self.task_dir = task_dir
        self.policy = load_policy(task_dir / "policy.yaml")
        self.provider = provider
        self.prompts = PromptRenderer(task_dir / "prompts")
        self.result_model = TaskResult[self.content_model]

    @property
    def task_type(self) -> str:
        return self.policy.task_type

    # ── 세션 시작 ──────────────────────────────────────────────

    def start(
        self,
        raw_input: str,
        mode: CoachingMode = CoachingMode.STANDARD,
        profile: HarnessProfile | None = None,
    ) -> SessionState:
        state = SessionState(
            task_type=self.task_type,
            mode=mode,
            raw_input=raw_input,
            profile=profile or HarnessProfile(),
        )
        self.apply_defaults(state)
        self.diagnose(state)
        self.advance(state)
        return state

    def apply_defaults(self, state: SessionState) -> None:
        """[코드] kind=default 필드는 묻지 않고 기본값을 넣는다."""
        for f in self.policy.fields:
            if f.kind is FieldKind.DEFAULT and f.default is not None:
                state.facts[f.name] = InfoItem(value=f.default, source=InfoSource.DEFAULT)

    def diagnose(self, state: SessionState) -> None:
        """[LLM] 처음 입력에서 항목을 뽑는다. 뽑은 값은 확인 전이므로 가정으로만 둔다."""
        target = self.policy.raw_input_field
        if target and state.raw_input.strip():
            state.facts[target] = InfoItem(
                value=state.raw_input.strip(), source=InfoSource.USER_FREE_TEXT
            )
        diagnosis = self._call(state, "diagnose", Diagnosis)
        known = set(self.policy.labels)
        for item in diagnosis.extracted:
            if item.field in known and item.field not in state.facts:
                state.assumptions[item.field] = Assumption(
                    value=item.value,
                    source=InfoSource.AI_ASSUMPTION,
                    confidence=0.5,
                    reason="처음 입력에서 추출",
                )

    # ── 질문 ──────────────────────────────────────────────────

    def advance(self, state: SessionState) -> None:
        """준비도를 갱신하고 다음 질문을 정한다. 답하지 않은 이전 질문은 버린다."""
        self._drop_unanswered(state)
        state.readiness = self.readiness(state)
        question = self.select_question(state)
        state.pending_question = question
        if question is not None:
            state.asked_questions.append(AskedQuestion(question=question))
            state.status = SessionStatus.CLARIFYING
        else:
            state.status = SessionStatus.REVISING if state.result_stale else SessionStatus.CONFIRMING

    def select_question(self, state: SessionState) -> Question | None:
        """[코드] '모르겠어요' 중인 필드가 먼저, 그다음 policy 순서대로 미충족 필드."""
        if state.dont_know_levels:
            name, level = next(iter(state.dont_know_levels.items()))
            return self.make_easier_question(state, self.policy.field(name), level)
        if self.should_stop(state):
            return None
        remaining = self.remaining_fields(state)
        return self.base_question(state, remaining[0]) if remaining else None

    def remaining_fields(self, state: SessionState) -> list[FieldPolicy]:
        return [
            f
            for f in self.policy.fields
            if f.kind is not FieldKind.DEFAULT
            and f.name not in state.facts
            and f.name not in state.unknowns
        ]

    def base_question(self, state: SessionState, field: FieldPolicy) -> Question:
        options = _options(field.options)
        assumed = state.assumptions.get(field.name)
        if assumed is not None:
            options.insert(0, QuestionOption(id="assumed", label=assumed.value, ai_suggested=True))
        return Question(
            field=field.name, text=field.question, options=options, multi_select=field.multi_select
        )

    def make_easier_question(self, state: SessionState, field: FieldPolicy, level: int) -> Question:
        """'모르겠어요' 사다리: policy 사다리 → LLM 쉬운 질문 → AI 후보 제안 순으로 내려간다."""
        if level >= self.policy.max_easier_level:
            return self.propose_value(state, field, level)
        if level <= len(field.easier_questions):
            step = field.easier_questions[level - 1]
            return Question(
                field=field.name,
                text=step.question,
                options=_options(step.options),
                multi_select=field.multi_select,
                level=level,
            )
        generated = self._call(
            state,
            "easier_question",
            GeneratedQuestion,
            field=field,
            level=level,
            previous=self._asked_texts(state, field.name),
        )
        return Question(
            field=field.name,
            text=generated.text,
            options=_options(generated.options),
            multi_select=field.multi_select,
            level=level,
        )

    def propose_value(self, state: SessionState, field: FieldPolicy, level: int) -> Question:
        """[LLM] 사다리 바닥. 맥락으로 후보를 추정해 고르거나 고치게 한다."""
        proposed = self._call(
            state,
            "propose_value",
            ProposedValues,
            field=field,
            level=level,
            previous=self._proposed_labels(state, field.name),
        )
        options = [
            QuestionOption(id=f"p{level}_{i}", label=label, ai_suggested=True)
            for i, label in enumerate(proposed.candidates, start=1)
        ]
        return Question(
            field=field.name, text=proposed.text, options=options, level=level, is_ai_proposal=True
        )

    # ── 답변 ──────────────────────────────────────────────────

    @contextmanager
    def _atomic(self, state: SessionState) -> Iterator[None]:
        """블록이 예외로 끝나면 state를 시작 때로 되돌린다. 실패 기록(trace)만 남긴다."""
        snapshot = state.model_copy(deep=True)
        try:
            yield
        except Exception:
            for name in SessionState.model_fields:
                if name != "trace":
                    setattr(state, name, getattr(snapshot, name))
            raise

    def apply_answer(self, state: SessionState, answer: Answer) -> None:
        question = state.pending_question
        if question is None or question.question_id != answer.question_id:
            raise HarnessError("지금 답할 수 있는 질문이 아닙니다.")
        record = self._asked_record(state, question.question_id)
        with self._atomic(state):
            value = self._record_reply(state, question, answer)
            _mark_answered(record, answer.answer_type, value)
            self.advance(state)

    def revise_answer(self, state: SessionState, answer: Answer) -> None:
        """이전 답변 수정(IV-08). 결과가 이미 있으면 재생성이 필요하다고 표시한다."""
        record = state.find_asked(answer.question_id)
        if record is None or record.answer_type is None:
            raise HarnessError("수정할 수 있는 답변이 아닙니다.")
        field = record.question.field
        value, source = answer_to_fact(record.question, answer)
        with self._atomic(state):
            self._set_fact(state, field, value, source)
            _mark_answered(record, answer.answer_type, value)
            pending = state.pending_question
            if pending is not None and pending.field != field:
                # 다른 필드 질문이 이미 화면에 있다: 그대로 둔다(LLM 재호출·question_id 변경 없음).
                state.readiness = self.readiness(state)
            else:
                self.advance(state)

    def _record_reply(self, state: SessionState, question: Question, answer: Answer) -> str | None:
        """답변 종류에 맞게 state를 바꾸고, 기록할 값(없으면 None)을 돌려준다."""
        name = question.field
        match answer.answer_type:
            case AnswerType.DONT_KNOW:
                state.dont_know_levels[name] = question.level + 1
                return None
            case AnswerType.SKIP:
                state.dont_know_levels.pop(name, None)
                if name not in state.unknowns:
                    state.unknowns.append(name)
                return None
            case _:
                value, source = answer_to_fact(question, answer)
                self._set_fact(state, name, value, source)
                return value

    @staticmethod
    def _asked_record(state: SessionState, question_id: str) -> AskedQuestion:
        record = state.find_asked(question_id)
        if record is None:
            raise HarnessError("질문 기록을 찾을 수 없습니다.")
        return record

    # ── 준비도·종료 ───────────────────────────────────────────

    def readiness(self, state: SessionState) -> float:
        """[코드] 채워진 필드 가중치 비율. 사실 1.0, AI 가정 0.5, 미확인 0."""
        total = sum(f.weight for f in self.policy.fields)
        score = sum(
            f.weight
            * (1.0 if f.name in state.facts else 0.5 if f.name in state.assumptions else 0.0)
            for f in self.policy.fields
        )
        return round(score / total, 3) if total else 0.0

    def question_cap(self, state: SessionState) -> int:
        return self.policy.question_caps[state.mode]

    def asked_count(self, state: SessionState) -> int:
        """질문 상한에 세는 수: 답한 기본 질문. '모르겠어요' 재질문(level ≥ 1)과 지금 걸려 있는 질문은 세지 않는다."""
        return sum(
            1 for a in state.asked_questions if a.question.level == 0 and a.answer_type is not None
        )

    def should_stop(self, state: SessionState) -> bool:
        if self.asked_count(state) >= self.question_cap(state):
            return True
        musts = [f.name for f in self.policy.fields if f.kind is FieldKind.MUST_CONFIRM]
        return (
            all(name in state.facts for name in musts)
            and state.readiness >= self.policy.readiness_threshold
        )

    # ── 생성·검증 ─────────────────────────────────────────────

    def generate(self, state: SessionState) -> None:
        """[LLM] 현재 정보로 결과를 만든다. 언제든 부를 수 있다(설계서 원칙 8).

        먼저 계산하고 마지막에 반영한다. 실패하면 질문·입력은 그대로 두고 FAILED로만 표시한다.
        """
        state.status = SessionStatus.GENERATING
        try:
            result = to_generation_result(
                self._call_retrying_bad_output(state, "generate", self.result_model)
            )
            report = self.validate(state, result)
        except Exception as exc:
            self._fail_generation(state, exc)
            raise GenerationFailed(state.error) from exc
        self._drop_unanswered(state)
        state.trace.append(_validation_trace(report))
        state.result = result
        state.result_stale = False
        state.error = None
        state.validation = report
        state.status = SessionStatus.COMPLETED

    @staticmethod
    def _fail_generation(state: SessionState, exc: Exception) -> None:
        """[코드] 실패를 기록한다. 사용자에게 보이는 error에는 내부 사정을 싣지 않는다."""
        state.error = GENERIC_GENERATION_ERROR
        if not isinstance(exc, ProviderError):  # ProviderError는 _call이 이미 trace에 남겼다
            state.trace.append(TraceEntry(stage="generate", output={"error": repr(exc)}))
        state.status = SessionStatus.FAILED

    def validate(self, state: SessionState, result: GenerationResult) -> ValidationReport:
        """[코드 + LLM] 공통·과제 규칙을 돌린다. LLM 검토는 policy.llm_validation일 때만(비용)."""
        issues = collect_issues([*COMMON_VALIDATORS, *self.validators], state, result, self.policy)
        if self.policy.llm_validation:
            issues.extend(self._llm_review(state, result))
        return ValidationReport(issues=issues)

    def _llm_review(self, state: SessionState, result: GenerationResult) -> list[ValidationIssue]:
        """[LLM] AI 검토는 보조 수단이다. 실패해도 경고 하나로 줄이고 결과는 살린다."""
        try:
            return self._call(state, "validate", LLMReview, result_text=result.full_text).issues
        except ProviderError:
            return [ValidationIssue(rule="llm_review_unavailable", message="AI 검토를 하지 못했습니다.")]

    # ── 내부 도우미 ───────────────────────────────────────────

    def _call_retrying_bad_output(
        self, state: SessionState, stage: str, response_model: type[M]
    ) -> M:
        """스키마를 지키지 않은 응답(ProviderOutputError)이면 한 번만 다시 부른다."""
        schema = json.dumps(response_model.model_json_schema(), ensure_ascii=False, indent=2)
        try:
            return self._call(state, stage, response_model, output_schema=schema)
        except ProviderOutputError:
            return self._call(state, stage, response_model, output_schema=schema)

    def _call(self, state: SessionState, stage: str, response_model: type[M], **context: Any) -> M:
        """프롬프트를 렌더링해 Provider를 부르고, 성공이든 실패든 trace에 남긴다."""
        prompt = self.prompts.render(
            stage, state=state, policy=self.policy, profile=state.profile, **context
        )
        try:
            response = self.provider.complete(
                task_type=self.task_type, stage=stage, prompt=prompt, response_model=response_model
            )
            if response.parsed is None:
                raise ProviderOutputError(f"{stage} 단계 응답에 구조화된 결과가 없습니다.")
        except ProviderError as exc:
            state.trace.append(
                TraceEntry(
                    stage=stage,
                    input={"prompt": prompt},
                    output={"error": str(exc)},
                    provider=self.provider.name,
                )
            )
            raise
        state.trace.append(
            TraceEntry(
                stage=stage,
                input={"prompt": prompt},
                output=response.parsed.model_dump(mode="json"),
                provider=self.provider.name,
                usage=response.usage.model_dump(),
            )
        )
        return response.parsed  # type: ignore[return-value]

    def _drop_unanswered(self, state: SessionState) -> None:
        if state.asked_questions and state.asked_questions[-1].answer_type is None:
            state.asked_questions.pop()
        state.pending_question = None

    def _set_fact(self, state: SessionState, name: str, value: str, source: InfoSource) -> None:
        state.facts[name] = InfoItem(value=value, source=source)
        state.assumptions.pop(name, None)
        state.dont_know_levels.pop(name, None)
        if name in state.unknowns:
            state.unknowns.remove(name)
        if state.result is not None:
            state.result_stale = True

    @staticmethod
    def _asked_texts(state: SessionState, name: str) -> list[str]:
        return [a.question.text for a in state.asked_questions if a.question.field == name]

    @staticmethod
    def _proposed_labels(state: SessionState, name: str) -> list[str]:
        return [
            o.label
            for a in state.asked_questions
            if a.question.field == name and a.question.is_ai_proposal
            for o in a.question.options
        ]
