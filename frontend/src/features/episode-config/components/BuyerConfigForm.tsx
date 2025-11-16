'use client';

import { useState } from 'react';
import { useConfig } from '@/store/configStore';
import { Card } from '@/components/Card';
import { Input } from '@/components/Input';
import { NumberInput } from '@/components/NumberInput';
import { Button } from '@/components/Button';
import type { ShoppingItem } from '@/lib/types';
import { generateId } from '@/utils/helpers';

export function BuyerConfigForm() {
  const { buyer, updateBuyerName, addShoppingItem, updateShoppingItem, removeShoppingItem } = useConfig();
  const [isExpanded, setIsExpanded] = useState(true);

  const handleAddItem = () => {
    const newItem: ShoppingItem = {
      item_id: `item_${generateId()}`,
      item_name: '',
      quantity_needed: 1,
      min_price_per_unit: 0,
      max_price_per_unit: 100,
    };
    addShoppingItem(newItem);
  };

  return (
    <Card
      className="transition-all duration-200"
      header={
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between text-left"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-neutral-900">Buyer Purchase Plan</h2>
              <p className="text-sm text-neutral-600">Configure buyer and per-item constraints</p>
            </div>
          </div>
          <svg
            className={`w-5 h-5 text-neutral-400 transition-transform ${isExpanded ? 'transform rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      }
    >
      {isExpanded && (
        <div className="space-y-6">
          {/* Buyer Name */}
          <Input
            label="Buyer Name"
            value={buyer.name}
            onChange={(e) => updateBuyerName(e.target.value)}
            placeholder="Enter buyer name"
          />

          {/* Shopping List */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-3">
              Purchase Plan (Per-Item Constraints)
            </label>
            <div className="space-y-4">
              {buyer.shopping_list.map((item, index) => (
                <div key={item.item_id} className="bg-neutral-50 rounded-lg p-4 border border-neutral-200">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Input
                      label="Item Name"
                      value={item.item_name}
                      onChange={(e) => updateShoppingItem(index, { ...item, item_name: e.target.value })}
                      placeholder="e.g., Laptop"
                    />
                    <NumberInput
                      label="Quantity"
                      value={item.quantity_needed}
                      onChange={(e) => updateShoppingItem(index, { ...item, quantity_needed: Number(e.target.value) })}
                      min={1}
                    />
                    <NumberInput
                      label="Min Price (per unit)"
                      value={item.min_price_per_unit}
                      onChange={(e) => updateShoppingItem(index, { ...item, min_price_per_unit: Number(e.target.value) })}
                      min={0}
                      step={0.01}
                    />
                    <NumberInput
                      label="Max Price (per unit)"
                      value={item.max_price_per_unit}
                      onChange={(e) => updateShoppingItem(index, { ...item, max_price_per_unit: Number(e.target.value) })}
                      min={0}
                      step={0.01}
                    />
                  </div>
                  <div className="mt-3 flex justify-end">
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => removeShoppingItem(index)}
                    >
                      Remove Item
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            <Button
              variant="ghost"
              onClick={handleAddItem}
              className="mt-4"
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Add Item to Purchase Plan
            </Button>

            <p className="mt-2 text-sm text-neutral-500">
              Note: No global budget concept - each item has independent min/max price constraints
            </p>
          </div>
        </div>
      )}
    </Card>
  );
}

