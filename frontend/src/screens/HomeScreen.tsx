import type { SessionSummary, TaskSummary } from "../api/types";
import { latestByTask } from "../lib/sessions";

type Props = {
  tasks: TaskSummary[];
  sessions: SessionSummary[];
  onStart: (task: string) => void;
  onResume: (summary: SessionSummary) => void;
  onWork: () => void;
};

/** 홈: 과제 네 개 중 하나를 고른다. 진행 중인 세션이 있는 과제는 이어서 할 수 있다. */
export function HomeScreen({ tasks, sessions, onStart, onResume, onWork }: Props) {
  const latest = latestByTask(sessions);
  return (
    <section className="home stack">
      <p className="small">START YOUR PROJECT</p>
      <h1 className="screen-title">오늘 어떤 작업을 함께 해볼까요?</h1>
      <p className="muted">아래에서 하나만 고르세요. 다음 화면에서 하고 싶은 이야기를 보내면 코칭이 시작돼요.</p>
      <div className="taskgrid">
        {tasks.map((task) => {
          const resume = latest.get(task.task_type);
          return (
            <article key={task.task_type} className="card task stack">
              <p className="small">{task.title}</p>
              <h2>{task.heading}</h2>
              <p className="muted">{task.description}</p>
              <p className="muted">{`완성할 것 · ${task.deliverable}`}</p>
              <div className="task-actions">
                {resume ? (
                  <>
                    <button type="button" className="btn primary full" onClick={() => onResume(resume)}>
                      {`진행 중인 ${task.title} 이어하기 →`}
                    </button>
                    <button type="button" className="btn textbtn" onClick={() => onStart(task.task_type)}>
                      새로 시작하기
                    </button>
                  </>
                ) : (
                  <button type="button" className="btn full" onClick={() => onStart(task.task_type)}>
                    {`${task.title} 시작하기 →`}
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
      <div className="recent">
        <p className="muted grow">
          {sessions.length > 0
            ? "진행 중인 작업은 이 브라우저의 익명 사용자로 서버에 저장돼요."
            : "하나의 아이디어를 사업계획부터 마케팅 콘텐츠까지 이어서 정리해 보세요."}
        </p>
        <button type="button" className="btn" onClick={onWork}>
          내 작업 보기
        </button>
      </div>
    </section>
  );
}
