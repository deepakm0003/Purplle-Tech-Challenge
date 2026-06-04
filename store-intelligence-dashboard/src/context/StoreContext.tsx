import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { apiClient } from '../services/apiClient';

export const STORES = [
  { id: 'ST1008', name: 'Store 1' },
  { id: 'ST2002', name: 'Store 2' },
] as const;

type StoreId = (typeof STORES)[number]['id'];

interface StoreContextValue {
  storeId: StoreId;
  storeName: string;
  setStoreId: (id: StoreId) => void;
}

const StoreContext = createContext<StoreContextValue | null>(null);

const DEFAULT_STORE =
  (import.meta.env.VITE_STORE_ID as StoreId) || 'ST1008';

export const StoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [storeId, setStoreIdState] = useState<StoreId>(DEFAULT_STORE);

  const storeName = useMemo(
    () => STORES.find((s) => s.id === storeId)?.name ?? storeId,
    [storeId]
  );

  const setStoreId = (id: StoreId) => {
    setStoreIdState(id);
    apiClient.setStoreId(id);
  };

  useEffect(() => {
    apiClient.setStoreId(storeId);
  }, [storeId]);

  const value = useMemo(
    () => ({ storeId, storeName, setStoreId }),
    [storeId, storeName]
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
};

export function useStore(): StoreContextValue {
  const ctx = useContext(StoreContext);
  if (!ctx) {
    throw new Error('useStore must be used within StoreProvider');
  }
  return ctx;
}
