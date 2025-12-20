'use client';
import { ChakraProvider } from '@chakra-ui/react';
import { GraphProvider } from '@/contexts/GraphContext';
import { ModeProvider } from '@/contexts/ModeContext';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ChakraProvider>
      <ModeProvider>
        <GraphProvider>
          {children}
        </GraphProvider>
      </ModeProvider>
    </ChakraProvider>
  );
}

