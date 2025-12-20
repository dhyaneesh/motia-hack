'use client';
import { createContext, useContext, useState, ReactNode, useCallback } from 'react';

export type Mode = 'default' | 'shopping' | 'study';

interface ModeContextType {
  currentMode: Mode;
  modeHistory: Mode[];
  setMode: (mode: Mode) => void;
  autoDetectMode: (query: string) => void;
  preserveState: () => void;
  restoreState: (mode: Mode) => void;
  savedStates: Record<Mode, any>;
}

const ModeContext = createContext<ModeContextType | undefined>(undefined);

export function ModeProvider({ children }: { children: ReactNode }) {
  const [currentMode, setCurrentMode] = useState<Mode>('default');
  const [modeHistory, setModeHistory] = useState<Mode[]>(['default']);
  const [savedStates, setSavedStates] = useState<Record<Mode, any>>({
    default: null,
    shopping: null,
    study: null
  });

  const setMode = useCallback((mode: Mode) => {
    // Preserve current state before switching
    preserveState();
    
    setCurrentMode(mode);
    setModeHistory(prev => [...prev, mode]);
  }, []);

  const autoDetectMode = useCallback((query: string) => {
    const queryLower = query.toLowerCase();
    
    // Shopping keywords
    const shoppingKeywords = [
      'buy', 'purchase', 'shop', 'shopping', 'price', 'prices', 'cost', 'costs',
      'cheap', 'affordable', 'discount', 'sale', 'deal', 'best price', 'compare prices',
      'where to buy', 'buy online', 'retailer', 'store'
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
        setMode('shopping');
        return;
      }
    }
    
    // Check for study intent
    for (const keyword of studyKeywords) {
      if (queryLower.includes(keyword)) {
        setMode('study');
        return;
      }
    }
    
    // Default fallback
    setMode('default');
  }, []);

  const preserveState = useCallback(() => {
    // This will be called from GraphContext to save graph state
    // The actual state preservation is handled in GraphContext
  }, []);

  const restoreState = useCallback((mode: Mode) => {
    // This will be called from GraphContext to restore graph state
    // The actual state restoration is handled in GraphContext
    setCurrentMode(mode);
  }, []);

  return (
    <ModeContext.Provider
      value={{
        currentMode,
        modeHistory,
        setMode,
        autoDetectMode,
        preserveState,
        restoreState,
        savedStates
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
