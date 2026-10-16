import type { TaskSummary } from "../api/types";

type Props = { tasks: TaskSummary[]; onStart: (task: string) => void };

/** 홈: 과제 네 개 중 하나를 고른다. */
export function HomeScreen({ tasks, onStart }: Props) {
  return (
    <section className="home stack">
      <p className="small">START YOUR PROJECT</p>
      <h1 className="screen-title">오늘 어떤 작업을 함께 해볼까요?</h1>
      <p className="muted">아래에서 하나만 고르세요. 다음 화면에서 하고 싶은 이야기를 보내면 코칭이 시작돼요.</p>
      <div className="taskgrid">
        {tasks.map((task) => (
          <article key={task.task_type} className="card task stack">
            <p className="small">{task.title}</p>
            <h2>{task.heading}</h2>
            <p className="muted">{task.description}</p>
            <p className="muted">{`완성할 것 · ${task.deliverable}`}</p>
            <button type="button" className="btn full" onClick={() => onStart(task.task_type)}>
              {`${task.title} 시작하기 →`}
            </button>
          </article>
        ))}
      </div>
      <p className="muted">하나의 아이디어를 사업계획부터 마케팅 콘텐츠까지 이어서 정리해 보세요.</p>
    </section>
  );
}
