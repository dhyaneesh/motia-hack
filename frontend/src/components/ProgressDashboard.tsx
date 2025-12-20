'use client';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Progress,
  Badge,
  Divider
} from '@chakra-ui/react';
import { useGraph } from '@/contexts/GraphContext';

type MasteryLevel = 'not_started' | 'learning' | 'mastered';

interface ConceptProgress {
  id: string;
  name: string;
  level: number;
  mastery: MasteryLevel;
  timeSpent: number; // in minutes
}

export function ProgressDashboard() {
  const { graph } = useGraph();
  
  // Extract concepts from graph and calculate progress
  const concepts: ConceptProgress[] = graph?.nodes?.map(node => ({
    id: node.id,
    name: node.data?.name || 'Unknown',
    level: node.data?.level || 2,
    mastery: 'learning' as MasteryLevel, // Would be tracked in state/database
    timeSpent: 0 // Would be tracked in state/database
  })) || [];
  
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
  
  if (concepts.length === 0) {
    return (
      <Box p={4} bg="white" borderRight="1px" borderColor="gray.200">
        <Text fontSize="sm" color="gray.500" fontStyle="italic">
          Complete a study query to track progress
        </Text>
      </Box>
    );
  }
  
  return (
    <Box
      w="100%"
      h="100vh"
      overflowY="auto"
      p={4}
      bg="white"
    >
      <Heading size="sm" mb={4}>Progress Dashboard</Heading>
      
      <VStack align="stretch" spacing={4}>
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
          <VStack align="stretch" spacing={2} maxH="400px" overflowY="auto">
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
    </Box>
  );
}
