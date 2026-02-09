import React from 'react';
import styles from './SetupChecklist.module.css';
import { useChecklistData } from '../../hooks/useChecklistData';
import { trackChecklistEvent } from '../../utils/analytics_events';

interface SetupChecklistProps {
  userId: string;
}

export const SetupChecklist: React.FC<SetupChecklistProps> = ({ userId }) => {
  const { steps, loading, updateStep } = useChecklistData(userId);

  if (loading) return <div>Loading checklist...</div>;

  const completedCount = steps.filter((s: any) => s.completed).length;
  const progress = steps.length > 0 ? (completedCount / steps.length) * 100 : 0;

  const handleToggle = (stepId: number, currentStatus: boolean) => {
    const newStatus = !currentStatus;
    updateStep(stepId, newStatus);
    trackChecklistEvent('checklist_step_toggled', { stepId, completed: newStatus });
  };

  return (
    <div className={styles.container}>
      <h3>Setup Progress</h3>
      <div className={styles.progressBar}>
        <div className={styles.progressFill} style={{ width: `${progress}%` }} />
      </div>
      <ul className={styles.taskList}>
        {steps.map((step: any) => (
          <li key={step.id} className={styles.taskItem}>
            <input
              type="checkbox"
              checked={step.completed}
              onChange={() => handleToggle(step.id, step.completed)}
            />
            <a href={step.link}>{step.title}</a>
          </li>
        ))}
      </ul>
    </div>
  );
