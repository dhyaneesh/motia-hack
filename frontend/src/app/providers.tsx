'use client';
import { ChakraProvider } from '@chakra-ui/react';
import { GraphProvider } from '@/contexts/GraphContext';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ChakraProvider>
      <GraphProvider>
        {children}
      </GraphProvider>
    </ChakraProvider>
  );
}

