'use client';
import {
  Box,
  Button,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  VStack,
  HStack,
  Text,
  Heading,
  Badge,
  Divider
} from '@chakra-ui/react';
import { useGraph } from '@/contexts/GraphContext';
import { useMode } from '@/contexts/ModeContext';
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

export function ExpandableLearningPath() {
  const { graph, selectNode } = useGraph();
  const { currentMode } = useMode();
  
  // Only show in study mode when graph has nodes
  if (currentMode !== 'study' || !graph || graph.nodes.length === 0) {
    return null;
  }
  
  // Extract learning path from graph nodes
  const learningPath: LearningPathItem[] = graph.nodes
    .map(node => ({
      id: node.id,
      name: node.data?.name || 'Unknown',
      level: node.data?.level ?? 'Concept',
      position: node.data?.learningPathPosition ?? 0
    }))
    .sort((a, b) => a.position - b.position);
  
  if (learningPath.length === 0) {
    return null;
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
    <Box position="absolute" top={4} left={4} zIndex={10}>
      <Popover placement="bottom-start">
        <PopoverTrigger>
          <Button size="sm" colorScheme="green" variant="outline">
            Learning Path
          </Button>
        </PopoverTrigger>
        <PopoverContent w="300px" maxH="500px" overflowY="auto">
          <PopoverBody>
            <VStack align="stretch" spacing={3}>
              <Heading size="sm">Learning Path</Heading>
              {learningPath.map((item, index) => (
                <Box key={item.id}>
                  <HStack spacing={2} align="start">
                    <Box
                      w="24px"
                      h="24px"
                      borderRadius="full"
                      bg="green.500"
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
                  {index < learningPath.length - 1 && (
                    <Box pl={3} mt={2}>
                      <Divider orientation="vertical" h="20px" borderColor="gray.300" />
                    </Box>
                  )}
                </Box>
              ))}
            </VStack>
          </PopoverBody>
        </PopoverContent>
      </Popover>
    </Box>
  );
}
