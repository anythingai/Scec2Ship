CREATE TABLE checklist_steps (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    link VARCHAR(255),
    order_index INT NOT NULL
);

CREATE TABLE user_checklist_progress (
    user_id INT NOT NULL,
    step_id INT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    PRIMARY KEY (user_id, step_id),
