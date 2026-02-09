import React, { createContext, useContext, useState } from 'react';

const UserContext = createContext<any>(null);

export const UserProvider: React.FC<{ children: React.BeNode }> = ({ children }) => {
  const [user, setUser] = useState({ id: 'user-123', onboardingCompleted: false });

  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => useContext(UserContext);
