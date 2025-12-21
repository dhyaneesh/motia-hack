'use client';
import { createContext, useContext, useState, ReactNode, useCallback } from 'react';

export type Mode = 'default' | 'shopping' | 'study';

interface ModeContextType {
  currentMode: Mode;
  modeHistory: Mode[];
  autoDetectEnabled: boolean;
  setMode: (mode: Mode) => void;
  toggleAutoDetect: () => void;
  autoDetectMode: (query: string) => Mode;
}

const ModeContext = createContext<ModeContextType | undefined>(undefined);

export function ModeProvider({ children }: { children: ReactNode }) {
  const [currentMode, setCurrentMode] = useState<Mode>('default');
  const [modeHistory, setModeHistory] = useState<Mode[]>(['default']);
  const [autoDetectEnabled, setAutoDetectEnabled] = useState<boolean>(false);

  const setMode = useCallback((mode: Mode) => {
    setCurrentMode(mode);
    setModeHistory(prev => [...prev, mode]);
  }, []);

  const toggleAutoDetect = useCallback(() => {
    setAutoDetectEnabled(prev => !prev);
  }, []);

  const autoDetectMode = useCallback((query: string): Mode => {
    const queryLower = query.toLowerCase();
    
    // Shopping keywords
    const shoppingKeywords = [
      'buy', 'purchase', 'shop', 'shopping', 'price', 'prices', 'cost', 'costs',
      'cheap', 'affordable', 'discount', 'sale', 'deal', 'best price', 'compare prices',
      'where to buy', 'buy online', 'retailer', 'store', 'amazon', 'ebay', 'walmart'
    ];
    
    // Study keywords
    const studyKeywords = [
      'explain', 'learn', 'learn about', 'how does', 'what is', 'what are',
      'understand', 'concept', 'theory', 'principle', 'definition', 'meaning',
      'tutorial', 'guide', 'study', 'learn how', 'teach me', 'help me understand'
    ];
    
    // Check for shopping intent
    for (const keyword of shoppingKeywords) {
      if (queryLower.includes(keyword)) {
        return 'shopping';
      }
    }
    
    // Check for study intent
    for (const keyword of studyKeywords) {
      if (queryLower.includes(keyword)) {
        return 'study';
      }
    }
    
    // Default fallback
    return 'default';
  }, []);

  return (
    <ModeContext.Provider
      value={{
        currentMode,
        modeHistory,
        autoDetectEnabled,
        setMode,
        toggleAutoDetect,
        autoDetectMode
      }}
    >
      {children}
    </ModeContext.Provider>
  );
}

export const useMode = () => {
  const context = useContext(ModeContext);
  if (!context) throw new Error('useMode must be used within ModeProvider');
  return context;
};
