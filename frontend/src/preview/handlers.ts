import type { Handlers } from "../app/view";

const noop = () => {};

/** 미리보기·테스트용. 버튼을 눌러도 아무 일도 하지 않는다. */
export const NOOP_HANDLERS: Handlers = {
  navigate: noop,
  guide: noop,
  goHome: noop,
  retry: noop,
  start: noop,
  changeDraft: noop,
  submitRequest: noop,
  editRequest: noop,
  pickMode: noop,
  answer: noop,
  example: noop,
  earlyDraft: noop,
  edit: noop,
  revise: noop,
  backToQuestions: noop,
  generate: noop,
  showResult: noop,
  confirm: noop,
  continueQuestions: noop,
};
