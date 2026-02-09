CREATE TABLE onboarding_tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    order_index INT NOT NULL
);

CREATE TABLE user_onboarding_progress (
    user_id INT NOT NULL,
    task_id INT NOT NULL REFERENCES onboarding_tasks(id),
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, task_id)
);

INSERT INTO onboarding_tasks (title, description, order_index) VALUES
('Create Account', 'Set up your profile and credentials.', 1),
('Verify Email', 'Confirm your email address to secure your account.', 2),
('Complete Profile', 'Add your personal details and preferences.', 3),
