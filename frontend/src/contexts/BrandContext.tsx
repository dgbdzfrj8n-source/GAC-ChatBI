'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

export type Brand = '全部' | '广汽埃安' | '广汽传祺' | '昊铂';

interface BrandContextType {
  brand: Brand;
  setBrand: (b: Brand) => void;
}

const BrandContext = createContext<BrandContextType>({
  brand: '全部',
  setBrand: () => {},
});

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brand, setBrand] = useState<Brand>('全部');
  return (
    <BrandContext.Provider value={{ brand, setBrand }}>
      {children}
    </BrandContext.Provider>
  );
}

export const useBrand = () => useContext(BrandContext);
