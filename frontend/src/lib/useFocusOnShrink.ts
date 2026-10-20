import { useEffect, useRef } from "react";

import { listShrank } from "./sessions";

/** 목록 개수가 줄면(항목이 사라지고 대화상자도 닫힌 뒤) 목록 제목으로 포커스를 옮긴다. */
export function useFocusOnShrink(count: number) {
  const heading = useRef<HTMLHeadingElement>(null);
  const previous = useRef(count);
  useEffect(() => {
    if (listShrank(previous.current, count)) heading.current?.focus();
    previous.current = count;
  }, [count]);
  return heading;
}
