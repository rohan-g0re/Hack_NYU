'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import type { BuyerConfig, SellerConfig, LLMConfig, ShoppingItem, InventoryItem } from '@/lib/types';
import { SellerPriority, SpeakingStyle, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS, DEFAULT_PROVIDER } from '@/lib/constants';

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
  loadSampleData: () => void;
  resetConfig: () => void;
}

const ConfigContext = createContext<ConfigContextValue | undefined>(undefined);

const initialBuyer: BuyerConfig = {
  name: '',
  shopping_list: [],
};

const initialLLMConfig: LLMConfig = {
  model: 'qwen/qwen3-1.7b',  // Default LM Studio model
  temperature: DEFAULT_TEMPERATURE,
  max_tokens: DEFAULT_MAX_TOKENS,
  provider: DEFAULT_PROVIDER,
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
    console.log('[ConfigStore] updateLLMConfig called with:', config);
    setState((prev) => {
      const newLLMConfig = { ...prev.llmConfig, ...config };
      console.log('[ConfigStore] Previous llmConfig:', prev.llmConfig);
      console.log('[ConfigStore] New llmConfig:', newLLMConfig);
      return {
        ...prev,
        llmConfig: newLLMConfig,
      };
    });
  }, []);

  const loadSampleData = useCallback(() => {
    const sampleBuyer: BuyerConfig = {
      name: 'John Doe',
      shopping_list: [
        {
          item_id: 'item_001',
          item_name: 'Laptop',
          quantity_needed: 2,
          min_price_per_unit: 900,
          max_price_per_unit: 1200,
        },
        {
          item_id: 'item_002',
          item_name: 'Mouse',
          quantity_needed: 5,
          min_price_per_unit: 15,
          max_price_per_unit: 25,
        },
      ],
    };

    const sampleSellers: SellerConfig[] = [
      {
        name: 'TechStore',
        inventory: [
          {
            item_id: 'item_001',
            item_name: 'Laptop',
            cost_price: 800,
            selling_price: 1200,
            least_price: 1000,
            quantity_available: 10,
          },
        ],
        profile: {
          priority: SellerPriority.CUSTOMER_RETENTION,
          speaking_style: SpeakingStyle.VERY_SWEET,
        },
      },
      {
        name: 'GadgetHub',
        inventory: [
          {
            item_id: 'item_001',
            item_name: 'Laptop',
            cost_price: 750,
            selling_price: 1150,
            least_price: 950,
            quantity_available: 5,
          },
          {
            item_id: 'item_002',
            item_name: 'Mouse',
            cost_price: 10,
            selling_price: 30,
            least_price: 20,
            quantity_available: 50,
          },
        ],
        profile: {
          priority: SellerPriority.MAXIMIZE_PROFIT,
          speaking_style: SpeakingStyle.RUDE,
        },
      },
      {
        name: 'CompuWorld',
        inventory: [
          {
            item_id: 'item_001',
            item_name: 'Laptop',
            cost_price: 820,
            selling_price: 1180,
            least_price: 1020,
            quantity_available: 8,
          },
          {
            item_id: 'item_002',
            item_name: 'Mouse',
            cost_price: 12,
            selling_price: 28,
            least_price: 18,
            quantity_available: 100,
          },
        ],
        profile: {
          priority: SellerPriority.CUSTOMER_RETENTION,
          speaking_style: SpeakingStyle.VERY_SWEET,
        },
      },
    ];

    // Preserve the current llmConfig (including provider selection)
    setState((prev) => ({
      buyer: sampleBuyer,
      sellers: sampleSellers,
      llmConfig: prev.llmConfig, // Keep existing LLM config
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
    loadSampleData,
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

