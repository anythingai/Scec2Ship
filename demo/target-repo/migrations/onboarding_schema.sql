CREATE TABLE onboarding_steps (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    step_order INTEGER NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_onboarding_progress (
    user_id INTEGER NOT NULL,
    step_id INTEGER REFERENCES onboarding_steps(id),
    status VARCHAR(50) DEFAULT 'pending',
    completed_at TIMESTAMP,
    PRIMARY KEY (user_id, step_id)
);

INSERT INTO onboarding_steps (title, description, step_order) VALUES
('Profile Setup', 'Complete your personal information.', 1),
('Email Verification', 'Verify your email address to secure your account.', 2),
('First Project', 'Create your first project to get started.', 3),
('Invite Team', 'Invite your colleagues to collaborate.', 4);
