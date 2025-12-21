'use client';
import { Box, Flex } from '@chakra-ui/react';
import dynamic from 'next/dynamic';
import { ChatInterface } from '@/components/ChatInterface';
import { NodeDetailSidebar } from '@/components/NodeDetailSidebar';
import { BuildLearningPathButton } from '@/components/BuildLearningPathButton';
import { useGraph } from '@/contexts/GraphContext';

// Dynamic import to avoid SSR issues with React Flow
const KnowledgeGraph = dynamic(() => import('@/components/KnowledgeGraph').then(mod => ({ default: mod.KnowledgeGraph })), { 
  ssr: false 
});

export default function Home() {
  const { isSidebarOpen } = useGraph();
  
  return (
    <Flex h="100vh" overflow="hidden">
      {/* Chat Panel - Fixed width */}
      <Box w="350px" borderRight="1px" borderColor="gray.200">
        <ChatInterface />
      </Box>
      
      {/* Graph Panel - Flexible width */}
      <Box flex={1} position="relative">
        <KnowledgeGraph />
        <BuildLearningPathButton />
      </Box>
      
      {/* Sidebar - Unified for all modes */}
      {isSidebarOpen && (
        <Box w="400px" borderLeft="1px" borderColor="gray.200">
          <NodeDetailSidebar />
        </Box>
      )}
    </Flex>
  );
}

