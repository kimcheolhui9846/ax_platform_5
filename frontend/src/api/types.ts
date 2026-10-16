import type { components } from "./schema";

type Schemas = components["schemas"];

export type TaskSummary = Schemas["TaskSummary"];
export type SessionView = Schemas["SessionView"];
export type ResultView = Schemas["ResultView"];
export type Question = Schemas["Question"];
export type Progress = Schemas["Progress"];
export type SummaryItem = Schemas["SummaryItem"];
export type AnswerRequest = Schemas["AnswerRequest"];
export type AnswerBody = Omit<AnswerRequest, "question_id">;
export type CoachingMode = Schemas["CoachingMode"];
export type LabeledAssumption = Schemas["LabeledAssumption"];
export type UnknownItem = Schemas["UnknownItem"];
