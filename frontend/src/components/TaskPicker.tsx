import type { TaskSummary } from "../api/types";

type Props = {
  tasks: TaskSummary[];
  onPick: (task: TaskSummary) => void;
};

export function TaskPicker({ tasks, onPick }: Props) {
  return (
    <section>
      <h2>어떤 코칭을 받을까요?</h2>
      {tasks.map((t) => (
        <button key={t.task_type} type="button" className="task" onClick={() => onPick(t)}>
          <strong>{t.title}</strong>
          <span>{t.description}</span>
        </button>
      ))}
    </section>
  );
}
