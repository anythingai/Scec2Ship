import { useState, useEffect } from 'react';

export const useChecklistData = (userId: string) => {
  const [steps, setSteps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/checklist?user_id=${userId}`)
      .then(res => res.json())
      .then(data => {
        setSteps(data);
        setLoading(false);
      });
  }, [userId]);

  const updateStep = async (stepId: number, completed: boolean) => {
    await fetch('/api/checklist/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, step_id: stepId, completed }),
    });
    setSteps(prev => prev.map(s => s.id === stepId ? { ...s, completed } : s));
  };

  return { steps, loading, updateStep };
};
