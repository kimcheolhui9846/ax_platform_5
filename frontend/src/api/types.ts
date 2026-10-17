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
export type TaskForm = Schemas["TaskForm"];
export type ReviseBody = Schemas["ReviseAnswerRequest"];
export type FlowItem = Schemas["FlowItem"];
export type FlowStatus = Schemas["FlowStatus"];
export type ModeInfo = Schemas["ModeInfo"];
export type ResultCard = Schemas["ResultCard"];
export type VersionSummary = Schemas["VersionSummary"];
export type VersionView = Schemas["VersionView"];
export type VersionReason = Schemas["VersionReason"];
export type LabeledResult = Schemas["LabeledResult"];
export type ValidationIssue = Schemas["ValidationIssue"];
export type SessionSummary = Schemas["SessionSummary"];
