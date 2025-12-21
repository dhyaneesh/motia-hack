'use client';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Badge,
  Button,
  Divider
} from '@chakra-ui/react';
import { useGraph } from '@/contexts/GraphContext';
import { api } from '@/services/api';

interface LearningPathItem {
  id: string;
  name: string;
  level: number | string; // 1, 2, 3, or "Concept"
  position: number;
}

const levelColors: Record<number | string, string> = {
  1: 'green',
  2: 'yellow',
  3: 'red',
  'Concept': 'gray'
};

const levelLabels: Record<number | string, string> = {
  1: 'Beginner',
  2: 'Intermediate',
  3: 'Advanced',
  'Concept': 'Concept'
};

export function LearningPath() {
  const { graph, selectNode } = useGraph();
  
  // Extract learning path from graph nodes
  const learningPath: LearningPathItem[] = graph?.nodes
    ?.map(node => ({
      id: node.id,
      name: node.data?.name || 'Unknown',
      level: node.data?.level ?? 'Concept',
      position: node.data?.learningPathPosition ?? 0
    }))
    .sort((a, b) => a.position - b.position) || [];
  
  if (learningPath.length === 0) {
    return (
      <Box p={4} bg="white" borderRight="1px" borderColor="gray.200">
        <Text fontSize="sm" color="gray.500" fontStyle="italic">
          Complete a study query to see the learning path
        </Text>
      </Box>
    );
  }
  
  const handleConceptClick = async (conceptId: string) => {
    try {
      const details = await api.getNodeDetails(conceptId);
      selectNode(details);
    } catch (error) {
      console.error('Failed to load concept details:', error);
    }
  };
  
  return (
    <Box
      w="100%"
      h="100vh"
      overflowY="auto"
      p={4}
      bg="white"
    >
      <Heading size="sm" mb={4}>Learning Path</Heading>
      
      <VStack align="stretch" spacing={3}>
        {learningPath.map((item, index) => (
          <Box key={item.id}>
            <HStack spacing={2} align="start">
              {/* Step Number */}
              <Box
                w="24px"
                h="24px"
                borderRadius="full"
                bg="blue.500"
                color="white"
                display="flex"
                alignItems="center"
                justifyContent="center"
                fontSize="xs"
                fontWeight="bold"
                flexShrink={0}
              >
                {index + 1}
              </Box>
              
              {/* Concept Info */}
              <VStack align="stretch" spacing={1} flex={1}>
                <Button
                  variant="ghost"
                  size="sm"
                  justifyContent="flex-start"
                  textAlign="left"
                  onClick={() => handleConceptClick(item.id)}
                  p={0}
                  h="auto"
                >
                  <Text fontSize="sm" fontWeight="medium" noOfLines={2}>
                    {item.name}
                  </Text>
                </Button>
                <Badge
                  colorScheme={levelColors[item.level] || 'gray'}
                  fontSize="xs"
                  w="fit-content"
                >
                  {levelLabels[item.level] || 'Concept'}
                </Badge>
              </VStack>
            </HStack>
            
            {/* Connector Line */}
            {index < learningPath.length - 1 && (
              <Box pl={3} mt={2}>
                <Divider orientation="vertical" h="20px" borderColor="gray.300" />
              </Box>
            )}
          </Box>
        ))}
      </VStack>
    </Box>
  );
}
