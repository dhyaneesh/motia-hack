'use client';
import {
  Box,
  Button,
  Spinner,
  useToast
} from '@chakra-ui/react';
import { useState } from 'react';
import { useGraph } from '@/contexts/GraphContext';
import { useMode } from '@/contexts/ModeContext';
import { api } from '@/services/api';

export function BuildLearningPathButton() {
  const { graph, currentRequestId, setGraph } = useGraph();
  const { currentMode } = useMode();
  const [isBuilding, setIsBuilding] = useState(false);
  const toast = useToast();
  
  // Only show in study mode when graph exists but learning path is not built
  if (currentMode !== 'study' || !graph || graph.nodes.length === 0) {
    return null;
  }
  
  // Check if learning path is already built (nodes have learningPathPosition)
  // learningPathPosition is the definitive indicator that learning path was built
  const hasLearningPath = graph.nodes.some(node => node.data?.learningPathPosition !== undefined && node.data?.learningPathPosition !== null);
  if (hasLearningPath) {
    return null; // Don't show button if learning path is already built
  }
  
  const handleBuildLearningPath = async () => {
    if (!currentRequestId) {
      toast({
        title: 'Error',
        description: 'Request ID not found',
        status: 'error',
        duration: 3000
      });
      return;
    }
    
    setIsBuilding(true);
    try {
      // Show initial toast
      toast({
        title: 'Building Learning Path',
        description: 'Assigning levels and building optimal learning sequence...',
        status: 'info',
        duration: 5000,
        isClosable: true
      });
      
      // Call API to build learning path
      const response = await api.buildLearningPath(currentRequestId);
      
      // Poll for completion - wait until status is 'completed' with learning_path_built flag
      let attempts = 0;
      const maxAttempts = 90; // 3 minutes max (90 * 2 seconds)
      
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const status = await api.getChatStatus(currentRequestId);
        
        // Check if learning path is built - status should be 'completed' with learning_path_built flag
        if (status.status === 'completed' && status.graph) {
          // Check if graph has nodes with learningPathPosition (definitive indicator)
          const hasLearningPath = status.graph.nodes?.some(
            (node: any) => node.data?.learningPathPosition !== undefined && node.data?.learningPathPosition !== null
          );
          
          if (hasLearningPath) {
            // Update graph with learning path data
            setGraph(status.graph);
            toast({
              title: 'Success',
              description: 'Learning path built successfully!',
              status: 'success',
              duration: 3000,
              isClosable: true
            });
            break;
          }
        } else if (status.status === 'failed') {
          toast({
            title: 'Error',
            description: status.error || 'Failed to build learning path',
            status: 'error',
            duration: 5000,
            isClosable: true
          });
          break;
        }
        
        attempts++;
      }
      
      if (attempts >= maxAttempts) {
        // Final check
        const finalStatus = await api.getChatStatus(currentRequestId);
        if (finalStatus.status === 'completed' && finalStatus.graph) {
          const hasLearningPath = finalStatus.graph.nodes?.some(
            (node: any) => node.data?.learningPathPosition !== undefined && node.data?.learningPathPosition !== null
          );
          
          if (hasLearningPath) {
            setGraph(finalStatus.graph);
            toast({
              title: 'Success',
              description: 'Learning path built successfully!',
              status: 'success',
              duration: 3000
            });
          } else {
            toast({
              title: 'Timeout',
              description: 'Learning path building is taking longer than expected. Please check again later.',
              status: 'warning',
              duration: 5000
            });
          }
        } else {
          toast({
            title: 'Timeout',
            description: 'Learning path building is taking longer than expected. Please check again later.',
            status: 'warning',
            duration: 5000
          });
        }
      }
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to build learning path',
        status: 'error',
        duration: 5000,
        isClosable: true
      });
    } finally {
      setIsBuilding(false);
    }
  };
  
  return (
    <Box position="absolute" bottom={4} right={4} zIndex={10}>
      <Button
        size="md"
        colorScheme="green"
        onClick={handleBuildLearningPath}
        isLoading={isBuilding}
        loadingText="Building..."
        leftIcon={isBuilding ? <Spinner size="sm" /> : undefined}
      >
        Build Learning Path
      </Button>
    </Box>
  );
}
