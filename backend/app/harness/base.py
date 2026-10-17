"""모든 과제가 공유하는 하네스 파이프라인.

단계 하나 = 메서드 하나다. 과제 하네스(tasks/<task>/harness.py)는 바꾸고 싶은
단계만 오버라이드한다. 모든 LLM 호출은 _call()을 거쳐 trace에 남는다.
"""
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel

from app.core.results import (
    GenerationResult,
    ResultAssumption,
    TaskResult,
    ValidationIssue,
    ValidationReport,
    VersionReason,
    sections_from_cards,
    utcnow,
    with_section_text,
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
    ResultVersion,
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
        raise HarnessError(f"없는 선택지입니다: {', '.join(unknown)}")
    return ", ".join(labels[i] for i in option_ids)


def _free_text(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        raise HarnessError("직접 입력한 내용이 비어 있습니다.")
    return text


def to_generation_result(parsed: TaskResult) -> GenerationResult:
    """[코드·순수] LLM이 만든 TaskResult를 세션에 저장할 GenerationResult로 바꾼다."""
    return GenerationResult(
        sections=sections_from_cards(parsed.cards),
        assumptions=parsed.assumptions,
        full_text=parsed.full_text,
        content=parsed.content.model_dump(mode="json"),
    )


SESSION_ASSUMPTION_REASON = "대화 중 AI가 보완한 값"


def merge_assumptions(
    llm: list[ResultAssumption],
    session: Mapping[str, Assumption],
    labels: Mapping[str, str],
) -> list[ResultAssumption]:
    """[코드·순수] 결과의 가정 목록에 세션 가정을 코드로 합친다. LLM이 다시 적어 주길 믿지 않는다.

    LLM이 field에 라벨을 적었으면 내부 이름으로 바꾼다. 결과에 없는 세션 가정은 값·이유와 함께 덧붙인다.
    """
    name_of = {label: name for name, label in labels.items()}
    merged = [
        a if a.field in labels else a.model_copy(update={"field": name_of.get(a.field, a.field)})
        for a in llm
    ]
    present = {a.field for a in merged}
    merged.extend(
        ResultAssumption(
            field=name,
            value=item.value,
            reason=item.reason or SESSION_ASSUMPTION_REASON,
            requires_confirmation=item.requires_confirmation,
        )
        for name, item in session.items()
        if name not in present
    )
    return merged


def _validation_trace(report: ValidationReport) -> TraceEntry:
    """[코드·순수] 검증 결과 요약 기록. LLM 검토 호출 기록과 kind로 구분한다."""
    return TraceEntry(
        stage="validate",
        output={"kind": "summary", "issues": [i.model_dump() for i in report.issues]},
    )


def reply_fact(question: Question, answer: Answer) -> tuple[str, InfoSource] | None:
    """[코드·순수] 값을 정하는 답이면 (값, 출처), '다른 예시 보기'·'아직 모르겠어요'(건너뛰기)면 None. 잘못된 입력은 HarnessError."""
    if answer.answer_type in (AnswerType.EASIER, AnswerType.SKIP):
        return None
    return answer_to_fact(question, answer)


def _values(items: Mapping[str, InfoItem]) -> dict[str, str]:
    return {name: item.value for name, item in items.items()}


def apply_supplements(current: Mapping[str, InfoItem], values: Mapping[str, str | None]) -> dict[str, InfoItem]:
    """[코드·순수] 보완 정보에 입력을 반영한 새 사전. 앞뒤 공백을 지우고, 빈 값·None이면 그 항목을 지운다."""
    merged = dict(current)
    for name, value in values.items():
        text = (value or "").strip()
        if not text:
            merged.pop(name, None)
        elif name not in merged or merged[name].value != text:
            merged[name] = InfoItem(value=text, source=InfoSource.USER_SUPPLEMENT)
    return merged


def supplements_changed(current: Mapping[str, InfoItem], latest: ResultVersion | None) -> bool:
    """[코드·순수] 보완 정보가 마지막 결과 버전에 반영된 것과 다른지(결과가 없으면 입력이 있는지)."""
    if latest is None:
        return bool(current)
    return _values(current) != _values(latest.supplements)


def generate_reason(state: SessionState) -> VersionReason:
    """[코드·순수] 이번 생성의 버전 이유. 답은 그대로이고 보완 정보만 바뀌었으면 보완 반영이다."""
    if not state.versions:
        return VersionReason.FIRST
    latest = state.versions[-1]
    same_answers = (
        _values(state.facts) == _values(latest.facts)
        and _values(state.assumptions) == _values(latest.assumptions)
        and list(state.unknowns) == latest.unknowns
    )
    if same_answers and supplements_changed(state.supplements, latest):
        return VersionReason.SUPPLEMENT
    return VersionReason.REGENERATE


def new_version(state: SessionState, result: GenerationResult, report: ValidationReport) -> ResultVersion:
    """[코드·순수] 방금 만든 결과의 버전 기록. 그때의 사실·가정·미정·보완 정보를 복사해 함께 남긴다."""
    return ResultVersion.snapshot(
        len(state.versions) + 1,
        generate_reason(state),
        result,
        report,
        state.facts,
        state.assumptions,
        state.unknowns,
        state.supplements,
    )


def find_version(versions: Sequence[ResultVersion], number: int) -> ResultVersion | None:
    """[코드·순수] 번호로 버전을 찾는다. 없으면 None."""
    return next((v for v in versions if v.version == number), None)


def counted_fields(records: Sequence[AskedQuestion]) -> set[str]:
    """[코드·순수] 질문 상한에 센 필드: 기본 질문(level 0)에 한 번이라도 답한 필드.

    사다리 재질문(level ≥ 1)과 지금 걸려 있는 질문은 세지 않는다. '원래 예시 보기'로 같은 기본 질문을
    다시 받아도 필드 하나로 센다.
    """
    return {r.question.field for r in records if r.question.level == 0 and r.answer_type is not None}


def unresolved_fields(
    fields: Sequence[FieldPolicy], facts: Mapping[str, InfoItem], unknowns: Sequence[str]
) -> list[FieldPolicy]:
    """[코드·순수] 아직 물을 필드(정책 순서): 기본값 필드가 아니고, 값도 미정 표시도 없는 필드."""
    return [
        f
        for f in fields
        if f.kind is not FieldKind.DEFAULT and f.name not in facts and f.name not in unknowns
    ]


def question_status(pending: Question | None, result_stale: bool) -> SessionStatus:
    """[코드·순수] 질문 단계의 상태. 걸린 질문이 있으면 CLARIFYING, 없으면 결과가 낡았는지에 따라 REVISING/CONFIRMING."""
    if pending is not None:
        return SessionStatus.CLARIFYING
    return SessionStatus.REVISING if result_stale else SessionStatus.CONFIRMING


def _settle_status(state: SessionState) -> None:
    """질문 흐름이 상태를 정하는 곳은 여기 한 곳이다(FAILED·COMPLETED도 여기서 벗어난다)."""
    state.status = question_status(state.pending_question, state.result_stale)


@contextmanager
def _atomic(state: SessionState) -> Iterator[None]:
    """블록이 예외로 끝나면 state를 시작 때로 되돌린다. 실패 기록(trace)만 남긴다."""
    snapshot = state.model_copy(deep=True)
    try:
        yield
    except Exception:
        for name in SessionState.model_fields:
            if name != "trace":
                setattr(state, name, getattr(snapshot, name))
        raise


def _mark_answered(record: AskedQuestion, answer_type: AnswerType, value: str | None) -> None:
    record.answer_type = answer_type
    record.value = value
    record.answered_at = utcnow()


def _supersede_others(records: list[AskedQuestion], current: AskedQuestion) -> None:
    """current가 필드 값을 정했다. 같은 필드의 다른 답한 기록은 지난 것으로 표시한다."""
    for record in records:
        if record is not current and record.question.field == current.question.field and record.answer_type:
            record.superseded = True
    current.superseded = False


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
        owner_id: str = "",
    ) -> SessionState:
        state = SessionState(
            task_type=self.task_type,
            mode=mode,
            raw_input=raw_input,
            profile=profile or HarnessProfile(),
            owner_id=owner_id,
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
        if question is not None:
            self._pose(state, question)
        _settle_status(state)

    def resume(self, state: SessionState) -> None:
        """결과를 만든 뒤에도 질문을 이어 간다. 결과는 언제든 만들 수 있고, 일찍 만들었다고 질문이 끝나지 않는다.

        이미 걸린 질문이 있으면 그 질문으로 돌아간다(실패한 생성 뒤 FAILED였다면 CLARIFYING이 된다).
        걸린 질문이 없을 때만 평소 규칙(select_question)으로 다음 질문을 고른다. 고를 질문이 없으면
        (상한·종료 조건) 세션을 그대로 둔다. 결과는 stale로 만들지 않는다. 새 답이 _set_fact로 표시한다.
        """
        if state.pending_question is not None:
            _settle_status(state)
            return
        with _atomic(state):
            question = self.select_question(state)
            if question is not None:
                self._pose(state, question)
                _settle_status(state)

    @staticmethod
    def _pose(state: SessionState, question: Question) -> None:
        """질문을 화면에 건다(질문을 거는 곳은 여기 한 곳). 상태는 호출한 쪽이 _settle_status로 정한다."""
        state.pending_question = question
        state.asked_questions.append(AskedQuestion(question=question))

    def select_question(self, state: SessionState) -> Question | None:
        """[코드] '다른 예시 보기' 중인 필드가 먼저, 그다음 policy 순서대로 미충족 필드."""
        if state.easier_levels:
            name, level = next(iter(state.easier_levels.items()))
            return self.make_easier_question(state, self.policy.field(name), level)
        if self.should_stop(state):
            return None
        remaining = self.remaining_fields(state)
        return self.base_question(state, remaining[0]) if remaining else None

    def remaining_fields(self, state: SessionState) -> list[FieldPolicy]:
        return unresolved_fields(self.policy.fields, state.facts, state.unknowns)

    def base_question(self, state: SessionState, field: FieldPolicy) -> Question:
        options = _options(field.options)
        assumed = state.assumptions.get(field.name)
        if assumed is not None:
            options.insert(0, QuestionOption(id="assumed", label=assumed.value, ai_suggested=True))
        return Question(
            field=field.name, text=field.question, options=options, multi_select=field.multi_select
        )

    def make_easier_question(self, state: SessionState, field: FieldPolicy, level: int) -> Question:
        """'다른 예시 보기' 사다리: policy 사다리 → LLM 쉬운 질문 → AI 후보 제안 순으로 내려간다."""
        if level >= self.policy.max_easier_level:
            return self.propose_value(state, field, level)
        if level <= len(field.easier_questions):
            step = field.easier_questions[level - 1]
            return Question(
                field=field.name,
                text=step.question,
                options=_options(step.options),
                multi_select=step.multi_select,
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
            field=field.name,
            text=proposed.text,
            options=options,
            multi_select=field.multi_select,
            level=level,
            is_ai_proposal=True,
        )

    def show_original(self, state: SessionState) -> None:
        """'원래 예시 보기'. 사다리에 있는 필드를 기본 질문(level 0)으로 되돌린다. LLM을 부르지 않는다.

        사다리 단계를 지우므로 다시 '다른 예시 보기'를 누르면 첫 단계부터 내려간다.
        """
        question = state.pending_question
        if question is None or question.level == 0:
            raise HarnessError("기본 질문으로 돌아갈 사다리 질문이 없습니다.")
        field = self.policy.field(question.field)
        with _atomic(state):
            self._drop_unanswered(state)
            state.easier_levels.pop(field.name, None)
            self._pose(state, self.base_question(state, field))
            _settle_status(state)

    # ── 답변 ──────────────────────────────────────────────────

    def apply_answer(self, state: SessionState, answer: Answer) -> None:
        question = state.pending_question
        if question is None or question.question_id != answer.question_id:
            raise HarnessError("지금 답할 수 있는 질문이 아닙니다.")
        record = self._asked_record(state, question.question_id)
        fact = reply_fact(question, answer)
        with _atomic(state):
            self._apply_reply(state, question, answer.answer_type, fact)
            _mark_answered(record, answer.answer_type, fact[0] if fact else None)
            if fact is not None:
                _supersede_others(state.asked_questions, record)
            self.advance(state)

    def revise_answer(self, state: SessionState, answer: Answer) -> None:
        """이전 답변 수정(IV-08). 결과가 이미 있으면 재생성이 필요하다고 표시한다."""
        record = state.find_asked(answer.question_id)
        if record is None or record.answer_type is None:
            raise HarnessError("수정할 수 있는 답변이 아닙니다.")
        field = record.question.field
        value, source = answer_to_fact(record.question, answer)
        with _atomic(state):
            self._set_fact(state, field, value, source)
            _mark_answered(record, answer.answer_type, value)
            _supersede_others(state.asked_questions, record)
            pending = state.pending_question
            if pending is not None and pending.field != field:
                # 다른 필드 질문이 이미 화면에 있으면 그대로 둔다(LLM 재호출·question_id 변경 없음).
                # 다만 수정으로 이제 멈출 때가 됐고 그 질문이 기본 질문이면 내리고 질문을 끝낸다.
                # 사다리 질문(level ≥ 1)은 사용자가 답하는 중이고 다시 만들려면 호출이 들므로 둔다.
                state.readiness = self.readiness(state)
                if pending.level == 0 and self.should_stop(state):
                    self.advance(state)
                else:
                    _settle_status(state)  # 질문이 걸려 있으므로 CLARIFYING(실패한 생성 뒤의 FAILED도 벗어난다)
            else:
                self.advance(state)

    def _apply_reply(
        self,
        state: SessionState,
        question: Question,
        answer_type: AnswerType,
        fact: tuple[str, InfoSource] | None,
    ) -> None:
        """답변 종류에 맞게 state를 바꾼다. 값은 reply_fact가 미리 계산해 둔다."""
        name = question.field
        if fact is not None:
            self._set_fact(state, name, *fact)
        elif answer_type is AnswerType.EASIER:
            state.easier_levels[name] = question.level + 1
        else:
            state.easier_levels.pop(name, None)
            if name not in state.unknowns:
                state.unknowns.append(name)

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
        """질문 상한에 세는 수(counted_fields 참고)."""
        return len(counted_fields(state.asked_questions))

    def should_stop(self, state: SessionState) -> bool:
        if self.asked_count(state) >= self.question_cap(state):
            return True
        musts = [f.name for f in self.policy.fields if f.kind is FieldKind.MUST_CONFIRM]
        return (
            all(name in state.facts for name in musts)
            and state.readiness >= self.policy.readiness_threshold
        )

    def questions_left(self, state: SessionState) -> int:
        """앞으로 더 물을 수 있는 기본 질문 수(흐름 패널의 '예정' 개수). 멈출 때가 됐으면 0이다."""
        if self.should_stop(state):
            return 0
        return max(self.question_cap(state) - self.asked_count(state), 0)

    # ── 생성·검증 ─────────────────────────────────────────────

    def generate(self, state: SessionState) -> None:
        """[LLM] 현재 정보로 결과를 만든다. 언제든 부를 수 있다(설계서 원칙 8).

        먼저 계산하고 마지막에 반영한다. 실패하면 질문·입력은 그대로 두고 FAILED로만 표시한다.
        사용자에게 보일 문구는 하네스가 정하지 않는다. 뷰가 FAILED 상태에서 만든다.
        HarnessError(사용자 입력·규칙 문제)는 세션을 되돌린 채 그대로 올린다(API 422).
        """
        try:
            with _atomic(state):
                state.status = SessionStatus.GENERATING
                result = to_generation_result(
                    self._call_retrying_bad_output(state, "generate", self.result_model)
                )
                result.assumptions = merge_assumptions(
                    result.assumptions, state.assumptions, self.policy.labels
                )
                report = self.validate(state, result)
        except HarnessError:
            raise
        except Exception as exc:
            self._fail_generation(state, exc)
            raise GenerationFailed from exc
        self._drop_unanswered(state)
        state.trace.append(_validation_trace(report))
        state.result = result
        state.result_stale = False
        state.validation = report
        state.versions.append(new_version(state, result, report))
        state.status = SessionStatus.COMPLETED

    @staticmethod
    def _fail_generation(state: SessionState, exc: Exception) -> None:
        """[코드] 실패를 trace에 기록하고 FAILED로 표시한다. 내부 사정은 trace에만 남는다.

        이전 결과는 그대로 남기고 result_stale도 건드리지 않는다. 입력이 그대로면 이전 결과는 여전히
        지금 입력에 맞는 결과이고, 입력이 바뀌었다면 _set_fact가 이미 true로 해 두었다.
        FAILED는 다음 답변·수정·성공한 생성까지 이어진다.
        """
        if not isinstance(exc, ProviderError):  # ProviderError는 _call이 이미 trace에 남겼다
            state.trace.append(TraceEntry(stage="generate", output={"error": repr(exc)}))
        state.status = SessionStatus.FAILED

    def save_version(self, state: SessionState, number: int) -> ResultVersion | None:
        """[코드] 그 버전에 저장 표시를 한다. 없는 번호면 None(세션은 그대로). 다시 저장해도 그대로다."""
        version = find_version(state.versions, number)
        if version is not None:
            version.saved = True
        return version

    def edit_section(self, state: SessionState, order: int, text: str) -> bool:
        """[코드] 결과 섹션 하나의 글을 바꾼 새 버전(edit)을 만든다. LLM을 부르지 않는다.

        직전 버전의 기준(사실·가정·미정)을 이어받고, 결과의 최신 여부(result_stale)는 그대로 둔다. 코드 검증만 다시
        돈다. 결과가 없거나 그 섹션이 없으면 False(세션은 그대로). 빈 글이면 HarnessError.
        """
        cleaned = text.strip()
        if not cleaned:
            raise HarnessError("고칠 문구가 비어 있습니다.")
        if state.result is None or not state.versions:
            return False
        result = with_section_text(state.result, order, cleaned)
        if result is None:
            return False
        report = ValidationReport(issues=collect_issues([*COMMON_VALIDATORS, *self.validators], state, result, self.policy))
        state.versions.append(state.versions[-1].derived(len(state.versions) + 1, VersionReason.EDIT, result, report))
        state.result = result
        state.validation = report
        return True

    def set_supplements(self, state: SessionState, values: Mapping[str, str | None]) -> None:
        """미확인 정보를 저장한다(사용자 입력·검증 전). 바뀌면 결과는 최신이 아니게 되고, 다음 생성에 반영된다."""
        unknown = sorted(set(values) - set(self.policy.supplement_labels))
        if unknown:
            raise HarnessError(f"보완할 수 없는 항목입니다: {', '.join(unknown)}")
        merged = apply_supplements(state.supplements, values)
        if _values(merged) == _values(state.supplements):
            return
        state.supplements = merged
        if state.result is not None:
            state.result_stale = True
            _settle_status(state)

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
        """스키마를 지키지 않은 응답(ProviderOutputError)이면 한 번만 다시 부른다.

        출력 구조는 제공자가 response_model로 강제한다. 프롬프트에 스키마를 싣지 않는다.
        """
        try:
            return self._call(state, stage, response_model)
        except ProviderOutputError:
            return self._call(state, stage, response_model)

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
                    input={"system": prompt.system, "user": prompt.user},
                    output={"error": str(exc)},
                    provider=self.provider.name,
                )
            )
            raise
        state.trace.append(
            TraceEntry(
                stage=stage,
                input={"system": prompt.system, "user": prompt.user},
                output=response.parsed.model_dump(mode="json"),
                provider=self.provider.name,
                model=response.model,
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
        state.easier_levels.pop(name, None)
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
