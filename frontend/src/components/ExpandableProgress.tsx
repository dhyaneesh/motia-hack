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
  Progress,
  Badge,
  Divider
} from '@chakra-ui/react';
import { useState } from 'react';
import { useGraph } from '@/contexts/GraphContext';
import { useMode } from '@/contexts/ModeContext';

type MasteryLevel = 'not_started' | 'learning' | 'mastered';

interface ConceptProgress {
  id: string;
  name: string;
  level: number;
  mastery: MasteryLevel;
  timeSpent: number;
}

export function ExpandableProgress() {
  const { graph } = useGraph();
  const { currentMode } = useMode();
  const [isOpen, setIsOpen] = useState(false);
  
  // Only show in study mode when graph has nodes
  if (currentMode !== 'study' || !graph || graph.nodes.length === 0) {
    return null;
  }
  
  // Extract concepts from graph and calculate progress
  const concepts: ConceptProgress[] = graph.nodes.map(node => ({
    id: node.id,
    name: node.data?.name || 'Unknown',
    level: node.data?.level || 2,
    mastery: 'learning' as MasteryLevel, // Would be tracked in state/database
    timeSpent: 0 // Would be tracked in state/database
  }));
  
  const totalConcepts = concepts.length;
  const masteredConcepts = concepts.filter(c => c.mastery === 'mastered').length;
  const learningConcepts = concepts.filter(c => c.mastery === 'learning').length;
  const overallProgress = totalConcepts > 0 ? (masteredConcepts / totalConcepts) * 100 : 0;
  const totalTimeSpent = concepts.reduce((sum, c) => sum + c.timeSpent, 0);
  
  const getMasteryColor = (mastery: MasteryLevel) => {
    switch (mastery) {
      case 'mastered': return 'green';
      case 'learning': return 'yellow';
      default: return 'gray';
    }
  };
  
  const getMasteryLabel = (mastery: MasteryLevel) => {
    switch (mastery) {
      case 'mastered': return 'Mastered';
      case 'learning': return 'Learning';
      default: return 'Not Started';
    }
  };
  
  return (
    <Box position="absolute" bottom={4} right={4} zIndex={10}>
      <Popover isOpen={isOpen} onOpen={() => setIsOpen(true)} onClose={() => setIsOpen(false)} placement="top-end">
        <PopoverTrigger>
          <Box
            bg="white"
            p={3}
            borderRadius="md"
            boxShadow="md"
            border="1px"
            borderColor="gray.200"
            cursor="pointer"
            _hover={{ boxShadow: 'lg' }}
            minW="200px"
          >
            <VStack align="stretch" spacing={2}>
              <HStack justify="space-between">
                <Text fontSize="xs" fontWeight="medium" color="gray.600">
                  Progress
                </Text>
                <Text fontSize="xs" color="gray.500">
                  {masteredConcepts}/{totalConcepts}
                </Text>
              </HStack>
              <Progress value={overallProgress} colorScheme="green" size="sm" borderRadius="md" />
              <Text fontSize="xs" color="gray.500" textAlign="center">
                {overallProgress.toFixed(0)}% Complete
              </Text>
            </VStack>
          </Box>
        </PopoverTrigger>
        <PopoverContent w="350px" maxH="500px" overflowY="auto">
          <PopoverBody>
            <VStack align="stretch" spacing={4}>
              <Heading size="sm">Study Progress</Heading>
              
              {/* Overall Progress */}
              <Box>
                <HStack justify="space-between" mb={2}>
                  <Text fontSize="sm" fontWeight="medium">
                    Overall Progress
                  </Text>
                  <Text fontSize="sm" color="gray.600">
                    {masteredConcepts}/{totalConcepts}
                  </Text>
                </HStack>
                <Progress value={overallProgress} colorScheme="blue" size="lg" borderRadius="md" />
                <Text fontSize="xs" color="gray.500" mt={1}>
                  {overallProgress.toFixed(0)}% Complete
                </Text>
              </Box>
              
              <Divider />
              
              {/* Statistics */}
              <VStack align="stretch" spacing={2}>
                <HStack justify="space-between">
                  <Text fontSize="sm" color="gray.600">Total Concepts:</Text>
                  <Text fontSize="sm" fontWeight="medium">{totalConcepts}</Text>
                </HStack>
                <HStack justify="space-between">
                  <Text fontSize="sm" color="gray.600">Mastered:</Text>
                  <Badge colorScheme="green">{masteredConcepts}</Badge>
                </HStack>
                <HStack justify="space-between">
                  <Text fontSize="sm" color="gray.600">Learning:</Text>
                  <Badge colorScheme="yellow">{learningConcepts}</Badge>
                </HStack>
                <HStack justify="space-between">
                  <Text fontSize="sm" color="gray.600">Time Spent:</Text>
                  <Text fontSize="sm" fontWeight="medium">{totalTimeSpent} min</Text>
                </HStack>
              </VStack>
              
              <Divider />
              
              {/* Concept List */}
              <Box>
                <Text fontSize="sm" fontWeight="medium" mb={2}>
                  Concepts
                </Text>
                <VStack align="stretch" spacing={2} maxH="200px" overflowY="auto">
                  {concepts.map((concept) => (
                    <Box
                      key={concept.id}
                      p={2}
                      bg="gray.50"
                      borderRadius="md"
                      border="1px"
                      borderColor="gray.200"
                    >
                      <HStack justify="space-between" mb={1}>
                        <Text fontSize="xs" fontWeight="medium" noOfLines={1}>
                          {concept.name}
                        </Text>
                        <Badge
                          colorScheme={getMasteryColor(concept.mastery)}
                          fontSize="xx-small"
                        >
                          {getMasteryLabel(concept.mastery)}
                        </Badge>
                      </HStack>
                      {concept.timeSpent > 0 && (
                        <Text fontSize="xx-small" color="gray.500">
                          {concept.timeSpent} min
                        </Text>
                      )}
                    </Box>
                  ))}
                </VStack>
              </Box>
            </VStack>
          </PopoverBody>
        </PopoverContent>
      </Popover>
    </Box>
  );
}
