import { describe, expect, it } from "vitest";
import { NOTICE_TEXT, isPrivate, privateChanges } from "./privacy";

describe("privacy", () => {
  it("isPrivate는 목록에 있는 이름만 참", () => {
    expect(isPrivate(["a"], "a")).toBe(true);
    expect(isPrivate(["a"], "b")).toBe(false);
  });
  it("privateChanges는 바뀐 것만", () => {
    expect(privateChanges({ a: true, b: false }, { a: true, b: true })).toEqual({ b: true });
    expect(privateChanges({}, { a: false })).toEqual({ a: false });
  });
  it("고지 문구", () => {
    expect(NOTICE_TEXT).toBe(
      "입력 내용은 결과를 만들기 위해 외부 AI 서비스로 전송될 수 있어요. 개인정보(주민번호·연락처·계좌 등)는 자동으로 가려서 보내고, 'AI에 보내지 않음'으로 표시한 항목은 보내지 않아요. 공개 전 아이디어·영업비밀은 표시해 주세요.",
    );
  });
});
