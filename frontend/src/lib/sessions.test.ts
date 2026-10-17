import { describe, expect, it } from "vitest";

import { makeSessionSummary } from "../testing/factories";
import { clip, latestByTask, resumeLabel, resumeRoute, savedDocuments, stageLabel, versionIsStale, versionLine } from "./sessions";

describe("세션 요약 판단", () => {
  it("버전 한 줄", () => {
    expect(versionLine({ version: 1, reason: "first" })).toBe("V1 · 첫 초안");
    expect(versionLine({ version: 3, reason: "regenerate" })).toBe("V3 · 다시 만든 초안");
    expect(versionLine({ version: 4, reason: "edit" })).toBe("V4 · 문구 수정");
  });

  it("이어서 작업할 화면: 걸린 질문 → 결과 → 답변 확인", () => {
    expect(resumeRoute(makeSessionSummary({ has_question: true, has_result: true }))).toEqual({ name: "question", sessionId: "sess_1" });
    expect(resumeRoute(makeSessionSummary({ has_question: false, has_result: true }))).toEqual({ name: "result", sessionId: "sess_1" });
    expect(resumeRoute(makeSessionSummary({ has_question: false, has_result: false }))).toEqual({ name: "confirm", sessionId: "sess_1" });
  });

  it("진행 단계 문구", () => {
    expect(stageLabel(makeSessionSummary({ has_question: true }))).toBe("질문 진행 중");
    expect(stageLabel(makeSessionSummary({ has_question: false, has_result: false }))).toBe("답변 확인");
    expect(stageLabel(makeSessionSummary({ has_question: false, has_result: true, latest_version: 2 }))).toBe("결과 V2");
    expect(stageLabel(makeSessionSummary({ has_question: false, has_result: true, latest_version: 2, result_stale: true }))).toBe(
      "결과 V2 · 최신 아님",
    );
  });

  it("과제마다 가장 최근 세션(목록은 이미 최근 순이다)", () => {
    const newer = makeSessionSummary({ session_id: "s2" });
    const older = makeSessionSummary({ session_id: "s1" });
    const brand = makeSessionSummary({ session_id: "s3", task_type: "branding" });
    const latest = latestByTask([newer, older, brand]);
    expect(latest.get("product_planning")).toBe(newer);
    expect(latest.get("branding")).toBe(brand);
    expect(latest.get("marketing_content")).toBeUndefined();
  });

  it("결과물: 저장한 버전을 최근에 만든 순서로 모은다", () => {
    const v1 = { version: 1, created_at: "2026-10-16T09:00:00Z", reason: "first" as const, saved: true };
    const v3 = { version: 3, created_at: "2026-10-16T11:00:00Z", reason: "regenerate" as const, saved: true };
    const other = { version: 1, created_at: "2026-10-16T10:00:00Z", reason: "first" as const, saved: true };
    const a = makeSessionSummary({ session_id: "a", saved_versions: [v1, v3] });
    const b = makeSessionSummary({ session_id: "b", saved_versions: [other] });
    expect(savedDocuments([a, b]).map((d) => [d.session.session_id, d.version.version])).toEqual([
      ["a", 3],
      ["b", 1],
      ["a", 1],
    ]);
  });

  it("긴 글은 줄여 보여 준다", () => {
    expect(clip("한글 파우치", 10)).toBe("한글 파우치");
    expect(clip("한글을 활용한 파우치를 만들고 싶어요", 10)).toBe("한글을 활용한 파…");
    expect(clip("  여러   칸 띄움  ", 20)).toBe("여러 칸 띄움");
  });
});

describe("이어하기 문구와 버전 최신 여부", () => {
  it("결과까지 끝난 세션은 결과 이어 보기, 그 밖에는 진행 중인 과제 이어하기", () => {
    expect(resumeLabel(makeSessionSummary({ has_question: true }))).toBe("진행 중인 상품기획 이어하기 →");
    expect(resumeLabel(makeSessionSummary({ has_question: false, has_result: false }))).toBe("진행 중인 상품기획 이어하기 →");
    expect(resumeLabel(makeSessionSummary({ has_question: false, has_result: true }))).toBe("상품기획 결과 이어 보기 →");
  });

  it("지난 버전이거나, 지금 버전이라도 답이 바뀌었으면 최신이 아니다", () => {
    expect(versionIsStale({ latest: true }, { result_stale: false })).toBe(false);
    expect(versionIsStale({ latest: false }, { result_stale: false })).toBe(true);
    expect(versionIsStale({ latest: true }, { result_stale: true })).toBe(true);
  });
});
