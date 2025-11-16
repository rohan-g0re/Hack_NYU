'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import type { BuyerConfig, SellerConfig, LLMConfig, ShoppingItem, InventoryItem } from '@/lib/types';
import { DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS } from '@/lib/constants';

interface ConfigState {
  buyer: BuyerConfig;
  sellers: SellerConfig[];
  llmConfig: LLMConfig;
}

interface ConfigContextValue extends ConfigState {
  updateBuyerName: (name: string) => void;
  addShoppingItem: (item: ShoppingItem) => void;
  updateShoppingItem: (index: number, item: ShoppingItem) => void;
  removeShoppingItem: (index: number) => void;
  addSeller: (seller: SellerConfig) => void;
  updateSeller: (index: number, seller: SellerConfig) => void;
  removeSeller: (index: number) => void;
  updateLLMConfig: (config: Partial<LLMConfig>) => void;
  resetConfig: () => void;
}

const ConfigContext = createContext<ConfigContextValue | undefined>(undefined);

const initialBuyer: BuyerConfig = {
  name: '',
  shopping_list: [],
};

const initialLLMConfig: LLMConfig = {
  model: 'qwen/qwen3-1.7b',
  temperature: DEFAULT_TEMPERATURE,
  max_tokens: DEFAULT_MAX_TOKENS,
};

const initialState: ConfigState = {
  buyer: initialBuyer,
  sellers: [],
  llmConfig: initialLLMConfig,
};

export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ConfigState>(initialState);

  const updateBuyerName = useCallback((name: string) => {
    setState((prev) => ({
      ...prev,
      buyer: { ...prev.buyer, name },
    }));
  }, []);

  const addShoppingItem = useCallback((item: ShoppingItem) => {
    setState((prev) => ({
      ...prev,
      buyer: {
        ...prev.buyer,
        shopping_list: [...prev.buyer.shopping_list, item],
      },
    }));
  }, []);

  const updateShoppingItem = useCallback((index: number, item: ShoppingItem) => {
    setState((prev) => ({
      ...prev,
      buyer: {
        ...prev.buyer,
        shopping_list: prev.buyer.shopping_list.map((i, idx) => (idx === index ? item : i)),
      },
    }));
  }, []);

  const removeShoppingItem = useCallback((index: number) => {
    setState((prev) => ({
      ...prev,
      buyer: {
        ...prev.buyer,
        shopping_list: prev.buyer.shopping_list.filter((_, idx) => idx !== index),
      },
    }));
  }, []);

  const addSeller = useCallback((seller: SellerConfig) => {
    setState((prev) => ({
      ...prev,
      sellers: [...prev.sellers, seller],
    }));
  }, []);

  const updateSeller = useCallback((index: number, seller: SellerConfig) => {
    setState((prev) => ({
      ...prev,
      sellers: prev.sellers.map((s, idx) => (idx === index ? seller : s)),
    }));
  }, []);

  const removeSeller = useCallback((index: number) => {
    setState((prev) => ({
      ...prev,
      sellers: prev.sellers.filter((_, idx) => idx !== index),
    }));
  }, []);

  const updateLLMConfig = useCallback((config: Partial<LLMConfig>) => {
    setState((prev) => ({
      ...prev,
      llmConfig: { ...prev.llmConfig, ...config },
    }));
  }, []);

  const resetConfig = useCallback(() => {
    setState(initialState);
  }, []);

  const value: ConfigContextValue = {
    ...state,
    updateBuyerName,
    addShoppingItem,
    updateShoppingItem,
    removeShoppingItem,
    addSeller,
    updateSeller,
    removeSeller,
    updateLLMConfig,
    resetConfig,
  };

  return <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>;
}

export function useConfig() {
  const context = useContext(ConfigContext);
  if (context === undefined) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
}

