import type { ShoppingItem, InventoryItem, BuyerConfig, SellerConfig } from '@/lib/types';

export interface ValidationError {
  field: string;
  message: string;
}

/**
 * Validate that min price is less than max price
 */
export function validatePriceRange(minPrice: number, maxPrice: number): ValidationError | null {
  if (minPrice < 0) {
    return { field: 'minPrice', message: 'Minimum price cannot be negative' };
  }
  if (maxPrice < 0) {
    return { field: 'maxPrice', message: 'Maximum price cannot be negative' };
  }
  if (minPrice >= maxPrice) {
    return { field: 'priceRange', message: 'Minimum price must be less than maximum price' };
  }
  return null;
}

/**
 * Validate seller inventory item pricing
 */
export function validateSellerInventory(item: InventoryItem): ValidationError | null {
  if (item.cost_price < 0) {
    return { field: 'cost_price', message: 'Cost price cannot be negative' };
  }
  if (item.selling_price <= item.cost_price) {
    return { field: 'selling_price', message: 'Selling price must be greater than cost price' };
  }
  if (item.least_price <= item.cost_price) {
    return { field: 'least_price', message: 'Least price must be greater than cost price' };
  }
  if (item.least_price >= item.selling_price) {
    return { field: 'least_price', message: 'Least price must be less than selling price' };
  }
  if (item.quantity_available < 0) {
    return { field: 'quantity_available', message: 'Quantity cannot be negative' };
  }
  return null;
}

/**
 * Validate shopping item
 */
export function validateShoppingItem(item: ShoppingItem): ValidationError | null {
  if (!item.item_name || item.item_name.trim() === '') {
    return { field: 'item_name', message: 'Item name is required' };
  }
  if (item.quantity_needed < 1) {
    return { field: 'quantity_needed', message: 'Quantity must be at least 1' };
  }
  return validatePriceRange(item.min_price_per_unit, item.max_price_per_unit);
}

/**
 * Validate buyer configuration
 */
export function validateBuyerConfig(config: BuyerConfig): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!config.name || config.name.trim() === '') {
    errors.push({ field: 'buyer.name', message: 'Buyer name is required' });
  }

  if (config.shopping_list.length === 0) {
    errors.push({ field: 'buyer.shopping_list', message: 'At least one item is required' });
  }

  config.shopping_list.forEach((item, index) => {
    const error = validateShoppingItem(item);
    if (error) {
      errors.push({
        field: `buyer.shopping_list[${index}].${error.field}`,
        message: error.message,
      });
    }
  });

  return errors;
}

/**
 * Validate seller configuration
 */
export function validateSellerConfig(config: SellerConfig, index: number): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!config.name || config.name.trim() === '') {
    errors.push({ field: `seller[${index}].name`, message: 'Seller name is required' });
  }

  if (config.inventory.length === 0) {
    errors.push({ field: `seller[${index}].inventory`, message: 'At least one inventory item is required' });
  }

  config.inventory.forEach((item, itemIndex) => {
    const error = validateSellerInventory(item);
    if (error) {
      errors.push({
        field: `seller[${index}].inventory[${itemIndex}].${error.field}`,
        message: error.message,
      });
    }
  });

  return errors;
}

/**
 * Validate all sellers configuration
 */
export function validateSellersConfig(sellers: SellerConfig[]): ValidationError[] {
  const errors: ValidationError[] = [];

  if (sellers.length === 0) {
    errors.push({ field: 'sellers', message: 'At least one seller is required' });
  }

  if (sellers.length > 10) {
    errors.push({ field: 'sellers', message: 'Maximum 10 sellers allowed' });
  }

  sellers.forEach((seller, index) => {
    errors.push(...validateSellerConfig(seller, index));
  });

  return errors;
}

/**
 * Validate entire episode configuration
 */
export function validateEpisodeConfig(
  buyer: BuyerConfig,
  sellers: SellerConfig[]
): ValidationError[] {
  return [
    ...validateBuyerConfig(buyer),
    ...validateSellersConfig(sellers),
  ];
}

