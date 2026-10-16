"""모든 과제가 공유하는 하네스 파이프라인.

단계 하나 = 메서드 하나다. 과제 하네스(tasks/<task>/harness.py)는 바꾸고 싶은
단계만 오버라이드한다. 모든 LLM 호출은 _call()을 거쳐 trace에 남는다.
"""
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel

from app.core.results import utcnow
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
from app.harness.errors import HarnessError
from app.harness.policy import FieldKind, FieldPolicy, load_policy
from app.harness.prompting import PromptRenderer
from app.harness.stage_models import Diagnosis, GeneratedQuestion, ProposedValues
from app.providers.base import LLMProvider, ProviderError

M = TypeVar("M", bound=BaseModel)


def _options(labels: list[str]) -> list[QuestionOption]:
    return [QuestionOption(id=f"o{i}", label=label) for i, label in enumerate(labels, start=1)]


class BaseHarness:
    content_model: ClassVar[type[BaseModel]]

    def __init__(self, task_dir: Path, provider: LLMProvider) -> None:
        self.task_dir = task_dir
        self.policy = load_policy(task_dir / "policy.yaml")
        self.provider = provider
        self.prompts = PromptRenderer(task_dir / "prompts")

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

    def apply_answer(self, state: SessionState, answer: Answer) -> None:
        question = state.pending_question
        if question is None or question.question_id != answer.question_id:
            raise HarnessError("지금 답할 수 있는 질문이 아닙니다.")
        name = question.field
        value: str | None = None

        match answer.answer_type:
            case AnswerType.OPTION:
                value = self._option_value(question, answer.option_ids)
                self._set_fact(state, name, value, InfoSource.USER_SELECTED_AI_OPTION)
            case AnswerType.FREE_TEXT:
                value = self._free_text(answer.value)
                self._set_fact(state, name, value, InfoSource.USER_FREE_TEXT)
            case AnswerType.DONT_KNOW:
                state.dont_know_levels[name] = question.level + 1
            case AnswerType.SKIP:
                state.dont_know_levels.pop(name, None)
                if name not in state.unknowns:
                    state.unknowns.append(name)

        record = state.asked_questions[-1]
        record.answer_type = answer.answer_type
        record.value = value
        record.answered_at = utcnow()
        self.advance(state)

    def revise_answer(self, state: SessionState, answer: Answer) -> None:
        """이전 답변 수정(IV-08). 결과가 이미 있으면 재생성이 필요하다고 표시한다."""
        record = state.find_asked(answer.question_id)
        if record is None or record.answer_type is None:
            raise HarnessError("수정할 수 있는 답변이 아닙니다.")
        name = record.question.field

        match answer.answer_type:
            case AnswerType.OPTION:
                value = self._option_value(record.question, answer.option_ids)
                self._set_fact(state, name, value, InfoSource.USER_SELECTED_AI_OPTION)
            case AnswerType.FREE_TEXT:
                value = self._free_text(answer.value)
                self._set_fact(state, name, value, InfoSource.USER_FREE_TEXT)
            case _:
                raise HarnessError("수정은 선택지나 직접 입력으로만 할 수 있습니다.")

        record.answer_type = answer.answer_type
        record.value = value
        record.answered_at = utcnow()
        self.advance(state)

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

    # ── 내부 도우미 ───────────────────────────────────────────

    def _call(self, state: SessionState, stage: str, response_model: type[M], **context: Any) -> M:
        """프롬프트를 렌더링해 Provider를 부르고, 성공이든 실패든 trace에 남긴다."""
        prompt = self.prompts.render(
            stage, state=state, policy=self.policy, profile=state.profile, **context
        )
        try:
            response = self.provider.complete(
                task_type=self.task_type, stage=stage, prompt=prompt, response_model=response_model
            )
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
                output=response.parsed.model_dump(mode="json") if response.parsed else {"text": response.text},
                provider=response.model,
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

    @staticmethod
    def _free_text(value: str | None) -> str:
        text = (value or "").strip()
        if not text:
            raise HarnessError("직접 입력한 내용이 비어 있습니다.")
        return text

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
